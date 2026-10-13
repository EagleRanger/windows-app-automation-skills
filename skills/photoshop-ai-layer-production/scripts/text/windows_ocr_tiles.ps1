param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,
    [Parameter(Mandatory = $true)]
    [string]$OutputJson,
    [int]$TileSize = 2400,
    [int]$Overlap = 240,
    [string]$LanguageTag = 'zh-Hans-CN'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Wait-WinRtResult($Operation, [Type]$ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$imageItem = Get-Item -LiteralPath $ImagePath
$outputFullPath = [IO.Path]::GetFullPath($OutputJson)
$outputFolder = Split-Path -Parent $outputFullPath
if (-not (Test-Path -LiteralPath $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
}
if ($TileSize -le $Overlap -or $TileSize -gt 2600) {
    throw 'TileSize must be greater than Overlap and no more than 2600.'
}

$storageFile = Wait-WinRtResult (
    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]::GetFileFromPathAsync($imageItem.FullName)
) ([Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime])
$stream = Wait-WinRtResult (
    $storageFile.OpenAsync([Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime]::Read)
) ([Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime])
$decoder = Wait-WinRtResult (
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]::CreateAsync($stream)
) ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime])

$language = New-Object 'Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime' $LanguageTag
$engine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]::TryCreateFromLanguage($language)
if (-not $engine) {
    throw "Could not create Windows OCR engine for $LanguageTag"
}

$width = [int]$decoder.PixelWidth
$height = [int]$decoder.PixelHeight
$step = $TileSize - $Overlap
$xPositions = [System.Collections.Generic.List[int]]::new()
$yPositions = [System.Collections.Generic.List[int]]::new()
for ($x = 0; $x -lt $width; $x += $step) {
    $actual = [Math]::Min($x, [Math]::Max(0, $width - $TileSize))
    if (-not $xPositions.Contains($actual)) { $xPositions.Add($actual) }
}
for ($y = 0; $y -lt $height; $y += $step) {
    $actual = [Math]::Min($y, [Math]::Max(0, $height - $TileSize))
    if (-not $yPositions.Contains($actual)) { $yPositions.Add($actual) }
}

$records = [System.Collections.Generic.List[object]]::new()
$tileCount = $xPositions.Count * $yPositions.Count
$tileIndex = 0
foreach ($y in $yPositions) {
    foreach ($x in $xPositions) {
        $tileIndex++
        $tileWidth = [Math]::Min($TileSize, $width - $x)
        $tileHeight = [Math]::Min($TileSize, $height - $y)
        $transform = New-Object 'Windows.Graphics.Imaging.BitmapTransform, Windows.Graphics.Imaging, ContentType=WindowsRuntime'
        $bounds = New-Object 'Windows.Graphics.Imaging.BitmapBounds, Windows.Graphics.Imaging, ContentType=WindowsRuntime'
        $bounds.X = [uint32]$x
        $bounds.Y = [uint32]$y
        $bounds.Width = [uint32]$tileWidth
        $bounds.Height = [uint32]$tileHeight
        $transform.Bounds = $bounds

        $bitmap = Wait-WinRtResult (
            $decoder.GetSoftwareBitmapAsync(
                [Windows.Graphics.Imaging.BitmapPixelFormat, Windows.Graphics.Imaging, ContentType = WindowsRuntime]::Bgra8,
                [Windows.Graphics.Imaging.BitmapAlphaMode, Windows.Graphics.Imaging, ContentType = WindowsRuntime]::Premultiplied,
                $transform,
                [Windows.Graphics.Imaging.ExifOrientationMode, Windows.Graphics.Imaging, ContentType = WindowsRuntime]::IgnoreExifOrientation,
                [Windows.Graphics.Imaging.ColorManagementMode, Windows.Graphics.Imaging, ContentType = WindowsRuntime]::DoNotColorManage
            )
        ) ([Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime])
        $result = Wait-WinRtResult (
            $engine.RecognizeAsync($bitmap)
        ) ([Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime])

        foreach ($line in $result.Lines) {
            if (-not $line.Words -or $line.Words.Count -eq 0) { continue }
            $left = [double]::PositiveInfinity
            $top = [double]::PositiveInfinity
            $right = 0.0
            $bottom = 0.0
            foreach ($word in $line.Words) {
                $rect = $word.BoundingRect
                $left = [Math]::Min($left, $rect.X)
                $top = [Math]::Min($top, $rect.Y)
                $right = [Math]::Max($right, $rect.X + $rect.Width)
                $bottom = [Math]::Max($bottom, $rect.Y + $rect.Height)
            }
            $text = ([string]$line.Text).Trim()
            if ($text.Length -eq 0) { continue }
            $records.Add([pscustomobject]@{
                text = $text
                x = [int][Math]::Round($x + $left)
                y = [int][Math]::Round($y + $top)
                width = [int][Math]::Round($right - $left)
                height = [int][Math]::Round($bottom - $top)
                tile = $tileIndex
            })
        }
        $bitmap.Dispose()
        if (($tileIndex % 10) -eq 0 -or $tileIndex -eq $tileCount) {
            Write-Output ("tiles={0}/{1}|records={2}" -f $tileIndex, $tileCount, $records.Count)
        }
    }
}

$payload = [ordered]@{
    source = $imageItem.FullName
    width = $width
    height = $height
    language = $LanguageTag
    tile_size = $TileSize
    overlap = $Overlap
    raw_record_count = $records.Count
    records = $records
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outputFullPath -Encoding UTF8
$stream.Dispose()
Write-Output ("output={0}|records={1}" -f $outputFullPath, $records.Count)
