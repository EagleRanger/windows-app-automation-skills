param(
    [Parameter(Mandatory = $true)]
    [string]$RuntimeRoot,
    [int]$Port = 8188
)

$ErrorActionPreference = 'Stop'
$runtime = [IO.Path]::GetFullPath($RuntimeRoot)
$python = Join-Path $runtime 'venv\Scripts\python.exe'
$main = Join-Path $runtime 'ComfyUI\main.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Missing runtime Python: $python" }
if (-not (Test-Path -LiteralPath $main -PathType Leaf)) { throw "Missing ComfyUI: $main" }
& $python $main --listen 127.0.0.1 --port $Port --disable-auto-launch
exit $LASTEXITCODE
