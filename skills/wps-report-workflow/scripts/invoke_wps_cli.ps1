[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs,

    [ValidateRange(5, 600)]
    [int]$TimeoutSeconds = 90,

    [switch]$AllowVisibleWps
)

$ErrorActionPreference = 'Stop'

function Write-JsonError {
    param([string]$Code, [string]$Message, [hashtable]$Details = @{})
    [ordered]@{
        success = $false
        error = [ordered]@{
            code = $Code
            message = $Message
            details = $Details
        }
    } | ConvertTo-Json -Depth 6
}

function Get-AutomationWpsProcesses {
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^(wps|et|wpp)\.exe$' -and
        $_.CommandLine -like '*/Automation -Embedding*'
    })
}

$projectRoot = $env:WPS_LOCAL_AI_HOME
if ([string]::IsNullOrWhiteSpace($projectRoot)) {
    Write-JsonError -Code 'WPS_LOCAL_AI_HOME_MISSING' -Message '未设置 WPS_LOCAL_AI_HOME，无法定位隔离安装的 wps-cli。' -Details @{ expected_environment = 'WPS_LOCAL_AI_HOME' }
    exit 9
}
$wpsCli = Join-Path $projectRoot '.venv\Scripts\wps.exe'
if (-not (Test-Path -LiteralPath $wpsCli)) {
    Write-JsonError -Code 'WPS_CLI_NOT_INSTALLED' -Message '未找到隔离安装的 wps-cli。' -Details @{ expected = $wpsCli }
    exit 10
}

$unsafePdfMutations = @('merge', 'extract-pages', 'split', 'watermark')
if (
    $CommandArgs.Count -ge 2 -and
    $CommandArgs[0] -eq 'pdf' -and
    $CommandArgs[1] -in $unsafePdfMutations
) {
    Write-JsonError -Code 'WPS_PDF_UI_REQUIRED' -Message '当前 WPS 12.1 的 PDF 编辑接口会启动可见阅读器，已在后台入口预先拦截。请改用 PDF 文件工具，或在明确授权后使用一次性界面操作。' -Details @{
        command = $CommandArgs
        verified_version = '12.1.0.28043'
    }
    exit 30
}

$unverifiedWriterMutations = @('replace', 'merge', 'table-insert')
$blockedWriterCommand = $null
if (
    $CommandArgs.Count -ge 2 -and
    $CommandArgs[0] -eq 'writer' -and
    $CommandArgs[1] -in $unverifiedWriterMutations
) {
    $blockedWriterCommand = "writer.$($CommandArgs[1])"
}
if ($CommandArgs.Count -ge 1 -and $CommandArgs[0] -eq 'batch') {
    $batchCommands = $null
    $commandsIndex = [Array]::IndexOf($CommandArgs, '--commands')
    if ($commandsIndex -lt 0) { $commandsIndex = [Array]::IndexOf($CommandArgs, '-c') }
    if ($commandsIndex -ge 0 -and ($commandsIndex + 1) -lt $CommandArgs.Count) {
        try { $batchCommands = $CommandArgs[$commandsIndex + 1] | ConvertFrom-Json } catch {}
    }
    $inputIndex = [Array]::IndexOf($CommandArgs, '--input')
    if ($inputIndex -lt 0) { $inputIndex = [Array]::IndexOf($CommandArgs, '-i') }
    if ($inputIndex -ge 0 -and ($inputIndex + 1) -lt $CommandArgs.Count) {
        $inputPath = $CommandArgs[$inputIndex + 1]
        if (Test-Path -LiteralPath $inputPath -PathType Leaf) {
            try { $batchCommands = Get-Content -LiteralPath $inputPath -Raw | ConvertFrom-Json } catch {}
        }
    }
    foreach ($item in @($batchCommands)) {
        if ($item.command -in @('writer.replace', 'writer.merge', 'writer.table-insert')) {
            $blockedWriterCommand = [string]$item.command
            break
        }
    }
}
if ($blockedWriterCommand) {
    Write-JsonError -Code 'WPS_WRITER_MUTATION_UNVERIFIED' -Message '该 Writer 修改命令在 WPS 12.1 上出现过“返回成功但关闭重开未持久化”或插入位置不确定，已从生产入口隔离。' -Details @{
        command = $blockedWriterCommand
        verified_version = '12.1.0.28043'
    }
    exit 31
}

$blockedImpressCommand = $null
if (
    $CommandArgs.Count -ge 2 -and
    $CommandArgs[0] -eq 'impress' -and
    $CommandArgs[1] -eq 'transition-set'
) {
    $blockedImpressCommand = 'impress.transition-set'
}
if ($CommandArgs.Count -ge 1 -and $CommandArgs[0] -eq 'batch') {
    foreach ($item in @($batchCommands)) {
        if ($item.command -in @('impress.transition-set', 'impress.transition_set')) {
            $blockedImpressCommand = [string]$item.command
            break
        }
    }
}
if ($blockedImpressCommand) {
    Write-JsonError -Code 'WPS_IMPRESS_TRANSITION_UNVERIFIED' -Message '该切换效果命令在 WPS 12.1 上返回成功，但关闭重开后效果和持续时间恢复默认值，已从生产入口隔离。' -Details @{
        command = $blockedImpressCommand
        verified_version = '12.1.0.28043'
    }
    exit 32
}

# Resource leases replace the blanket "any WPS window is busy" rule.
# CLI services still use ActiveDocument/ActivePresentation and application-level
# teardown, so separate calls of the SAME component remain serialized. Different
# components can overlap. The backend checks the actual COM session before any
# mutation; -AllowVisibleWps cannot bypass that check.
$components = @('writer', 'calc', 'impress')
$requestedComponents = if ($CommandArgs[0] -in $components) {
    @($CommandArgs[0])
} elseif ($CommandArgs[0] -eq 'batch' -and $batchCommands) {
    @($batchCommands | ForEach-Object { ([string]$_.command).Split('.')[0] } |
        Where-Object { $_ -in $components } | Sort-Object -Unique)
} else {
    $components
}
if (-not $requestedComponents) { $requestedComponents = $components }
$resourceKeys = @($requestedComponents | ForEach-Object { "component:$_" })
# Also protect shared input/output paths, including cross-type PDF exports.
$pathCandidates = @($CommandArgs)
if ($CommandArgs[0] -eq 'batch' -and $batchCommands) {
    foreach ($item in $batchCommands) {
        $pathCandidates += @($item.params.PSObject.Properties | ForEach-Object { [string]$_.Value })
    }
}
foreach ($candidate in $pathCandidates) {
    if ([IO.Path]::IsPathRooted($candidate) -and $candidate -match '\.(doc[xm]?|xls[xmb]?|ppt[xm]?|pps[xm]?|wps|et|dps|rtf|txt|html?|pdf|csv|png|jpe?g)$') {
        $resourceKeys += 'file:' + [IO.Path]::GetFullPath($candidate).ToLowerInvariant()
    }
}
$leases = [Collections.Generic.List[Threading.Mutex]]::new()
foreach ($key in ($resourceKeys | Sort-Object -Unique)) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($key)
    $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))
    $lease = [Threading.Mutex]::new($false, "Local\wps-local-ai-$digest")
    $acquired = $false
    try { $acquired = $lease.WaitOne(0) } catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) {
        $lease.Dispose()
        foreach ($held in $leases) { $held.ReleaseMutex(); $held.Dispose() }
        Write-JsonError -Code 'WPS_RESOURCE_BUSY' -Message '只有当前组件会话或目标路径正在被另一项作业占用；其它类型和独立路径不受影响。' -Details @{ resource = $key }
        exit 21
    }
    $leases.Add($lease)
}

try {
$baselineIds = @(Get-AutomationWpsProcesses | ForEach-Object { [int]$_.ProcessId })
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $wpsCli
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.Environment['PYTHONUTF8'] = '1'
foreach ($arg in $CommandArgs) {
    [void]$psi.ArgumentList.Add($arg)
}

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $psi
if (-not $process.Start()) {
    Write-JsonError -Code 'PROCESS_START_FAILED' -Message '无法启动 wps-cli。'
    exit 11
}

$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$finished = $process.WaitForExit($TimeoutSeconds * 1000)

if (-not $finished) {
    try { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Milliseconds 500
    $observed = @(Get-AutomationWpsProcesses | Where-Object { $_.ProcessId -notin $baselineIds } | Select-Object ProcessId,ParentProcessId,CreationDate)
    Write-JsonError -Code 'WPS_COM_TIMEOUT' -Message "WPS COM 调用超过 ${TimeoutSeconds} 秒，已停止本次 CLI。未根据进程差集强杀 WPS，须核对本次目标与会话归属后恢复。" -Details @{
        command = $CommandArgs
        observed_new_processes_not_ownership_proof = $observed
    }
    exit 60
}

$process.WaitForExit()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()
Start-Sleep -Milliseconds 500
# Normal teardown belongs to the owned COM instance. A process that appeared
# after our baseline may belong to a concurrent job and must NEVER be reaped.

if ($stdout) { Write-Output $stdout -NoEnumerate }
if ($stderr) { [Console]::Error.Write($stderr) }

if ($process.ExitCode -ne 0) {
    exit $process.ExitCode
}

exit 0
} finally {
    foreach ($held in $leases) { $held.ReleaseMutex(); $held.Dispose() }
}
