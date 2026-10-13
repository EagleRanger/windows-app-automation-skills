param(
    [Parameter(Mandatory = $true)]
    [string]$ComfyRoot,
    [string]$ManifestPath = (Join-Path $PSScriptRoot '..\config\models.json'),
    [switch]$SkipHash
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$comfy = [IO.Path]::GetFullPath($ComfyRoot)
$manifestFile = Get-Item -LiteralPath $ManifestPath
$manifest = Get-Content -LiteralPath $manifestFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.schema -ne 'photoshop_ai_layer_models_v1') {
    throw "Unexpected model manifest schema: $($manifest.schema)"
}
if (-not (Test-Path -LiteralPath $comfy -PathType Container)) {
    throw "ComfyUI root does not exist: $comfy"
}

function Test-Model([string]$Path, $Entry) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne [int64]$Entry.bytes) { return $false }
    if ($SkipHash) { return $true }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq ([string]$Entry.sha256).ToLowerInvariant()
}

$http = [System.Net.Http.HttpClient]::new()
$http.Timeout = [TimeSpan]::FromDays(2)
try {
    foreach ($entry in $manifest.models) {
        $target = Join-Path $comfy ([string]$entry.relative_path).Replace('/', '\')
        $folder = Split-Path -Parent $target
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        if (Test-Model $target $entry) {
            Write-Output "verified=$target"
            continue
        }
        if (Test-Path -LiteralPath $target) {
            $quarantine = "$target.invalid.$((Get-Date).ToString('yyyyMMddHHmmss'))"
            Move-Item -LiteralPath $target -Destination $quarantine
            Write-Output "quarantined=$quarantine"
        }
        $part = "$target.part"
        $offset = if (Test-Path -LiteralPath $part) { (Get-Item -LiteralPath $part).Length } else { 0L }
        $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, [string]$entry.url)
        if ($offset -gt 0) { $request.Headers.Range = [System.Net.Http.Headers.RangeHeaderValue]::new($offset, $null) }
        Write-Output "downloading=$($entry.filename)|resume_bytes=$offset|expected_bytes=$($entry.bytes)"
        $response = $http.Send($request, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead)
        $response.EnsureSuccessStatusCode()
        $append = $offset -gt 0 -and [int]$response.StatusCode -eq 206
        if ($offset -gt 0 -and -not $append) { $offset = 0L }
        $mode = if ($append) { [IO.FileMode]::Append } else { [IO.FileMode]::Create }
        $input = $response.Content.ReadAsStream()
        $output = [IO.File]::Open($part, $mode, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $input.CopyTo($output, 8MB) } finally { $output.Dispose(); $input.Dispose(); $response.Dispose(); $request.Dispose() }
        if ((Get-Item -LiteralPath $part).Length -ne [int64]$entry.bytes) {
            throw "Downloaded size mismatch for $($entry.filename). The .part file is retained for resume."
        }
        if (-not $SkipHash) {
            $actual = (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -ne ([string]$entry.sha256).ToLowerInvariant()) {
                throw "SHA-256 mismatch for $($entry.filename). The .part file is retained for diagnosis."
            }
        }
        Move-Item -LiteralPath $part -Destination $target
        Write-Output "installed=$target"
    }
} finally {
    $http.Dispose()
}

Write-Output 'status=success'
