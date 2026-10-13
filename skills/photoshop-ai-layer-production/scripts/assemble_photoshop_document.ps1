param(
    [Parameter(Mandatory = $true)]
    [string]$JobJson
)

$ErrorActionPreference = 'Stop'
$jobFile = Get-Item -LiteralPath $JobJson
$job = Get-Content -LiteralPath $jobFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
if ($job.schema -ne 'photoshop_ai_layer_job_v1') { throw "Unexpected job schema: $($job.schema)" }
$source = Get-Item -LiteralPath $job.source_image
$output = [IO.Path]::GetFullPath([string]$job.output_document)
$extension = [IO.Path]::GetExtension($output).ToLowerInvariant()
if ($extension -notin @('.psd', '.psb')) { throw 'Output must be .psd or .psb.' }
if (Test-Path -LiteralPath $output) { throw "Refusing to overwrite existing output: $output" }
$outputFolder = Split-Path -Parent $output
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
$sourceHashBefore = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash

$seenNames = @{}
foreach ($layer in $job.layers) {
    $item = Get-Item -LiteralPath $layer.file
    if ($seenNames.ContainsKey([string]$layer.name)) { throw "Duplicate layer name: $($layer.name)" }
    $seenNames[[string]$layer.name] = $true
    $layer.file = $item.FullName
}

$photoshop = Get-Process -Name Photoshop -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 -and $_.Responding } |
    Select-Object -First 1
if (-not $photoshop) { throw 'No visible, responsive user-opened Photoshop instance was found.' }

if (-not ('PortablePsAttach' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PortablePsAttach
{
    [DllImport("oleaut32.dll", PreserveSig = false)]
    private static extern void GetActiveObject(ref Guid rclsid, IntPtr reserved, [MarshalAs(UnmanagedType.IUnknown)] out object ppunk);
    public static object Attach(string progId)
    {
        Type type = Type.GetTypeFromProgID(progId, true);
        Guid clsid = type.GUID;
        object instance;
        GetActiveObject(ref clsid, IntPtr.Zero, out instance);
        return instance;
    }
}
'@
}

$job.source_image = $source.FullName
$job.output_document = $output
$jobCompact = $job | ConvertTo-Json -Depth 12 -Compress
$expectedCount = [int]$job.layers.Count
$jsx = @"
(function () {
    app.displayDialogs = DialogModes.NO;
    if (app.documents.length < 1) throw new Error('Photoshop has no open document.');
    var job = $jobCompact;
    var doc = app.activeDocument;
    var actual = '';
    try { actual = doc.fullName.fsName; } catch (ignored) {}
    if (actual.toLowerCase() !== job.source_image.toLowerCase()) {
        throw new Error('Active document mismatch. Expected ' + job.source_image + ', got ' + actual);
    }
    if (doc.layers.length !== 1 || doc.layers[0].typename !== 'ArtLayer') {
        throw new Error('The source must be a flat raster document with exactly one root art layer.');
    }
    var width = Math.round(doc.width.as('px'));
    var height = Math.round(doc.height.as('px'));
    var reference = doc.layers[0];
    reference.name = job.reference_layer_name || '原图参考_锁定';
    reference.visible = job.reference_visible === true;
    try { reference.allLocked = true; } catch (ignoredLock) {}

    var groups = {};
    for (var g = job.groups.length - 1; g >= 0; g--) {
        var set = doc.layerSets.add();
        set.name = job.groups[g];
        groups[job.groups[g]] = set;
    }
    for (var i = job.layers.length - 1; i >= 0; i--) {
        var item = job.layers[i];
        if (!groups[item.group]) throw new Error('Unknown group for layer ' + item.name + ': ' + item.group);
        var file = new File(item.file);
        if (!file.exists) throw new Error('Missing layer asset: ' + item.file);
        var opened = app.open(file);
        if (Math.round(opened.width.as('px')) !== width || Math.round(opened.height.as('px')) !== height) {
            opened.close(SaveOptions.DONOTSAVECHANGES);
            throw new Error('Layer asset canvas mismatch: ' + item.file);
        }
        var duplicated = opened.activeLayer.duplicate(doc, ElementPlacement.PLACEATBEGINNING);
        opened.close(SaveOptions.DONOTSAVECHANGES);
        app.activeDocument = doc;
        duplicated.name = item.name;
        duplicated.visible = item.visible !== false;
        duplicated.move(groups[item.group], ElementPlacement.INSIDE);
    }

    var outputFile = new File(job.output_document);
    if (outputFile.exists) throw new Error('Refusing to overwrite output: ' + outputFile.fsName);
    if (job.output_document.toLowerCase().slice(-4) === '.psb') {
        var desc = new ActionDescriptor();
        desc.putObject(stringIDToTypeID('as'), stringIDToTypeID('largeDocumentFormat'), new ActionDescriptor());
        desc.putPath(stringIDToTypeID('in'), outputFile);
        desc.putBoolean(stringIDToTypeID('copy'), false);
        desc.putBoolean(stringIDToTypeID('lowerCase'), true);
        executeAction(stringIDToTypeID('save'), desc, DialogModes.NO);
    } else {
        var options = new PhotoshopSaveOptions();
        options.layers = true;
        options.embedColorProfile = true;
        doc.saveAs(outputFile, options, false, Extension.LOWERCASE);
    }
    doc.close(SaveOptions.DONOTSAVECHANGES);
    var reopened = app.open(outputFile);
    if (Math.round(reopened.width.as('px')) !== width || Math.round(reopened.height.as('px')) !== height) {
        throw new Error('Canvas changed after reopen.');
    }
    var found = 0;
    for (var j = 0; j < job.layers.length; j++) {
        var expected = job.layers[j];
        var layer = reopened.layerSets.getByName(expected.group).artLayers.getByName(expected.name);
        if (layer.visible !== (expected.visible !== false)) throw new Error('Visibility mismatch: ' + expected.name);
        found++;
    }
    var reopenedReference = reopened.artLayers.getByName(job.reference_layer_name || '原图参考_锁定');
    if (reopenedReference.visible !== (job.reference_visible === true)) throw new Error('Reference visibility mismatch.');
    return ['status=success','version=' + app.version,'path=' + reopened.fullName.fsName,'width=' + width,'height=' + height,'layers=' + found,'groups=' + job.groups.length,'saved=' + reopened.saved].join('|');
}());
"@

$app = [PortablePsAttach]::Attach('Photoshop.Application')
$result = [string]$app.DoJavaScript($jsx)
if (-not (Test-Path -LiteralPath $output -PathType Leaf)) { throw "Photoshop returned but output is missing: $output" }
$sourceHashAfter = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
$receipt = [ordered]@{
    schema = 'photoshop_assembly_receipt_v1'
    status = if ($sourceHashBefore -eq $sourceHashAfter) { 'success' } else { 'failed' }
    source = $source.FullName
    source_sha256_before = $sourceHashBefore
    source_sha256_after = $sourceHashAfter
    source_unchanged = $sourceHashBefore -eq $sourceHashAfter
    output = $output
    output_bytes = (Get-Item -LiteralPath $output).Length
    layer_count = $expectedCount
    photoshop_pid = $photoshop.Id
    photoshop_window = $photoshop.MainWindowTitle
    photoshop_result = $result
    completed_at = (Get-Date).ToString('o')
}
$receiptPath = "$output.receipt.json"
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
$receipt | ConvertTo-Json -Depth 5
if (-not $receipt.source_unchanged) { throw 'Source file hash changed unexpectedly.' }
