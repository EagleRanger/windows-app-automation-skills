using System;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using ArcGIS.Core.CIM;
using ArcGIS.Desktop.Mapping;
using ArcGISProMCP.Bridge;
namespace ArcGISProMCP.Commands
{
    // Local derivative: edit only an existing native raster colorizer.
    internal static class RasterPaletteCommands
    {
        public static void Register()
        {
            CommandRouter.Register("get_raster_palette", "symbology", "Read native raster classes and colours.", Read);
            CommandRouter.Register("set_raster_palette", "symbology", "Replace six class colours without changing raster values or class boundaries.", Set);
        }
        private static object Read(Params p)
        {
            var layer = MapHelpers.FindLayer(MapHelpers.ResolveMap(p), p.Require("layer_name"));
            var d = layer.GetDefinition() as CIMRasterLayer;
            var c = d?.Colorizer as CIMRasterUniqueValueColorizer;
            if (c == null) throw new ArgumentException("Raster has no native unique-value colorizer.");
            return new Dictionary<string, object> { ["layer"] = layer.Name, ["colorizer"] = c.ToJson() };
        }
        private static object Set(Params p)
        {
            var layer = MapHelpers.FindLayer(MapHelpers.ResolveMap(p), p.Require("layer_name"));
            var d = layer.GetDefinition() as CIMRasterLayer;
            var c = d?.Colorizer as CIMRasterUniqueValueColorizer;
            if (c == null) throw new ArgumentException("Raster has no native unique-value colorizer.");
            var colors = p.Raw("colors").EnumerateArray().Select(v => v.GetString()).ToArray();
            if (colors.Length != 6) throw new ArgumentException("Exactly six #RRGGBB colours required.");
            var classes = c.Groups.SelectMany(g => g.Classes).OrderBy(v => int.Parse(v.Values[0], CultureInfo.InvariantCulture)).ToArray();
            if (classes.Length != 6 || !classes.Select(v => int.Parse(v.Values[0], CultureInfo.InvariantCulture)).SequenceEqual(Enumerable.Range(1,6)))
                throw new ArgumentException("Expected native raster classes 1..6.");
            // Parse all colours first; an invalid request makes no map edit.
            var parsed = colors.Select(h => {
                if (h == null || h.Length != 7 || h[0] != '#') throw new ArgumentException("Use #RRGGBB colours.");
                return ColorFactory.Instance.CreateRGBColor(
                    int.Parse(h.Substring(1,2), NumberStyles.HexNumber), int.Parse(h.Substring(3,2), NumberStyles.HexNumber), int.Parse(h.Substring(5,2), NumberStyles.HexNumber), 100);
            }).ToArray();
            for (var i=0;i<6;i++) classes[i].Color = parsed[i];
            layer.SetDefinition(d);
            return Read(p);
        }
    }
}
