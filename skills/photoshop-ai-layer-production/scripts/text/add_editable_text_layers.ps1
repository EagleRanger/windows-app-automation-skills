param(
    [Parameter(Mandatory = $true)]
    [string]$ExpectedDocument,
    [Parameter(Mandatory = $true)]
    [string]$ManifestJson
)

$ErrorActionPreference = 'Stop'
$document = Get-Item -LiteralPath $ExpectedDocument
$manifestFile = Get-Item -LiteralPath $ManifestJson
$manifest = Get-Content -LiteralPath $manifestFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.schema -ne 'photoshop_editable_text_manifest_v1') { throw "Unexpected manifest schema: $($manifest.schema)" }
if ([int]$manifest.layer_count -ne $manifest.layers.Count) { throw 'Manifest layer count mismatch.' }

$photoshop = Get-Process -Name Photoshop -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 -and $_.Responding } |
    Select-Object -First 1
if (-not $photoshop) { throw 'No visible, responsive user-opened Photoshop instance was found.' }
if (-not ('PortableTextAttach' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PortableTextAttach
{
    [DllImport("oleaut32.dll", PreserveSig = false)]
    private static extern void GetActiveObject(ref Guid rclsid, IntPtr reserved, [MarshalAs(UnmanagedType.IUnknown)] out object ppunk);
    public static object Attach(string progId)
    {
        Type type = Type.GetTypeFromProgID(progId, true);
        Guid clsid = type.GUID; object instance;
        GetActiveObject(ref clsid, IntPtr.Zero, out instance);
        return instance;
    }
}
'@
}

$expected = $document.FullName.Replace('\', '\\').Replace("'", "\'")
$payload = $manifest | ConvertTo-Json -Depth 12 -Compress
$count = [int]$manifest.layer_count
$jsx = @"
(function () {
    app.displayDialogs = DialogModes.NO;
    var doc = app.activeDocument;
    var actual = ''; try { actual = doc.fullName.fsName; } catch (ignored) {}
    if (actual.toLowerCase() !== '$expected'.toLowerCase()) throw new Error('Active document mismatch: ' + actual);
    var manifest = $payload;
    if (Math.round(doc.width.as('px')) !== manifest.document.width_px || Math.round(doc.height.as('px')) !== manifest.document.height_px) throw new Error('Canvas mismatch.');
    try { doc.layerSets.getByName('可编辑文字_OCR_默认隐藏'); throw new Error('Text group already exists.'); }
    catch (e) { if (String(e).indexOf('already exists') >= 0) throw e; }
    var parent = doc.layerSets.add(); parent.name = '可编辑文字_OCR_默认隐藏';
    var groups = {};
    for (var i = 0; i < manifest.layers.length; i++) {
        var item = manifest.layers[i];
        if (!groups[item.group]) { var set = parent.layerSets.add(); set.name = item.group; groups[item.group] = set; }
        var layer = doc.artLayers.add(); layer.kind = LayerKind.TEXT; layer.name = item.name;
        var text = layer.textItem; text.kind = TextType.POINTTEXT; text.contents = item.text;
        text.position = [UnitValue(item.position_px[0], 'px'), UnitValue(item.position_px[1], 'px')];
        text.font = item.font; text.size = UnitValue(item.size_pt, 'pt');
        text.horizontalScale = item.horizontal_scale; text.verticalScale = item.vertical_scale; text.tracking = item.tracking;
        var color = new SolidColor(); color.rgb.red = item.color_rgb[0]; color.rgb.green = item.color_rgb[1]; color.rgb.blue = item.color_rgb[2]; text.color = color;
        layer.move(groups[item.group], ElementPlacement.INSIDE);
    }
    parent.visible = false; doc.save(); doc.close(SaveOptions.DONOTSAVECHANGES);
    var reopened = app.open(new File('$expected'));
    var check = reopened.layerSets.getByName('可编辑文字_OCR_默认隐藏');
    var found = 0;
    for (var g = 0; g < check.layerSets.length; g++) {
        for (var k = 0; k < check.layerSets[g].artLayers.length; k++) {
            if (check.layerSets[g].artLayers[k].kind !== LayerKind.TEXT) throw new Error('Non-text object found after reopen.');
            found++;
        }
    }
    if (found !== $count || check.visible) throw new Error('Text layer reopen verification failed.');
    return 'status=success|text_layers=' + found + '|group_visible=' + check.visible + '|saved=' + reopened.saved;
}());
"@
$app = [PortableTextAttach]::Attach('Photoshop.Application')
$result = [string]$app.DoJavaScript($jsx)
[ordered]@{
    schema = 'photoshop_text_layer_receipt_v1'
    status = 'success'
    document = $document.FullName
    document_bytes = (Get-Item -LiteralPath $document.FullName).Length
    manifest = $manifestFile.FullName
    text_layers = $count
    photoshop_result = $result
    completed_at = (Get-Date).ToString('o')
} | ConvertTo-Json -Depth 5
