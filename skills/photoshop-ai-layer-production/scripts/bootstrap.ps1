param(
    [Parameter(Mandatory = $true)]
    [string]$RuntimeRoot,
    [switch]$DownloadModels,
    [switch]$SourceOnly,
    [string]$PythonCommand = 'py'
)

$ErrorActionPreference = 'Stop'
$skillRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtime = [IO.Path]::GetFullPath($RuntimeRoot)
if ($runtime.TrimEnd('\') -eq [IO.Path]::GetPathRoot($runtime).TrimEnd('\') -or
    $runtime.TrimEnd('\') -eq [IO.Path]::GetFullPath($env:USERPROFILE).TrimEnd('\') -or
    $runtime.TrimEnd('\') -eq $skillRoot.TrimEnd('\')) {
    throw 'Choose a dedicated runtime directory, not a drive root, user root, or Skill root.'
}
$lock = Get-Content -LiteralPath (Join-Path $skillRoot 'config\runtime-lock.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$comfy = Join-Path $runtime 'ComfyUI'
$venv = Join-Path $runtime 'venv'
$python = Join-Path $venv 'Scripts\python.exe'

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)." }
}

function Get-VerifiedHead([string]$Checkout) {
    $value = @(& git -C $Checkout rev-parse HEAD)
    Assert-NativeSuccess 'Read Git HEAD'
    $value = ($value -join '').Trim()
    if ($value -notmatch '^[0-9a-f]{40}$') { throw 'Invalid Git HEAD.' }
    return $value
}

function Remove-CloneStaging([string]$Candidate) {
    $absolute = [IO.Path]::GetFullPath($Candidate)
    if ([IO.Path]::GetDirectoryName($absolute).TrimEnd('\') -ne $runtime.TrimEnd('\') -or
        [IO.Path]::GetFileName($absolute) -notmatch '^\.ComfyUI-[0-9a-f]{32}$') {
        throw 'Refusing cleanup outside the exact clone staging directory.'
    }
    if (Test-Path -LiteralPath $absolute) {
        $item = Get-Item -LiteralPath $absolute -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Refusing recursive cleanup of a reparse point.'
        }
        Remove-Item -LiteralPath $absolute -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $runtime -Force | Out-Null
if (-not (Test-Path -LiteralPath $comfy)) {
    $staging = Join-Path $runtime ('.ComfyUI-' + [guid]::NewGuid().ToString('N'))
    try {
        & git clone ([string]$lock.comfyui.repository) $staging
        Assert-NativeSuccess 'Clone ComfyUI'
        if (-not (Test-Path -LiteralPath (Join-Path $staging '.git') -PathType Container)) {
            throw 'Clone did not produce a Git checkout.'
        }
        if ((Get-VerifiedHead $staging) -ne [string]$lock.comfyui.commit) {
            & git -C $staging fetch origin ([string]$lock.comfyui.commit)
            Assert-NativeSuccess 'Fetch pinned ComfyUI commit'
            & git -C $staging checkout --detach ([string]$lock.comfyui.commit)
            Assert-NativeSuccess 'Checkout pinned ComfyUI commit'
        }
        if ((Get-VerifiedHead $staging) -ne [string]$lock.comfyui.commit) {
            throw 'ComfyUI HEAD differs from the pinned commit.'
        }
        Move-Item -LiteralPath $staging -Destination $comfy -ErrorAction Stop
    } catch {
        Remove-CloneStaging $staging
        throw
    }
}
if ((Get-Item -LiteralPath $comfy -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'ComfyUI runtime must not be a reparse point.'
}
$head = Get-VerifiedHead $comfy
if ($head -ne [string]$lock.comfyui.commit) {
    throw 'Existing ComfyUI checkout differs from the pinned commit; preserve it and choose a fresh runtime directory.'
}
if ($SourceOnly) {
    Write-Output "status=success|source_only=true|comfy=$comfy|commit=$head"
    return
}
if (-not (Test-Path -LiteralPath $python)) {
    if ($PythonCommand -eq 'py') {
        & py -3.12 -m venv $venv
    } else {
        & $PythonCommand -m venv $venv
    }
    Assert-NativeSuccess 'Create Python environment'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Python environment is incomplete.' }
& $python -m pip install --upgrade pip setuptools wheel
Assert-NativeSuccess 'Install Python build dependencies'
& $python -m pip install `
    "torch==$($lock.pytorch.torch)" `
    "torchvision==$($lock.pytorch.torchvision)" `
    "torchaudio==$($lock.pytorch.torchaudio)" `
    --index-url ([string]$lock.pytorch.index_url)
Assert-NativeSuccess 'Install PyTorch'
& $python -m pip install -r (Join-Path $skillRoot 'requirements-verified-cu126.txt')
Assert-NativeSuccess 'Install workflow dependencies'

if ($DownloadModels) {
    & (Join-Path $PSScriptRoot 'download_models.ps1') -ComfyRoot $comfy
}
& $python (Join-Path $PSScriptRoot 'check_environment.py') --comfy-root $comfy
if ($LASTEXITCODE -ne 0) { throw 'Environment check failed.' }
Write-Output "status=success|runtime=$runtime|comfy=$comfy|python=$python"
