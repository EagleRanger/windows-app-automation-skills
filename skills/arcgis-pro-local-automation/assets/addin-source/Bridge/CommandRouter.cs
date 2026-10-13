using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using ArcGIS.Desktop.Framework.Threading.Tasks;

namespace ArcGISProMCP.Bridge
{
    /// <summary>A command handler. Runs on the MCT unless registered otherwise.</summary>
    public delegate object CommandHandler(Params parameters);

    /// <summary>
    /// A handler that is already asynchronous, such as anything built on
    /// Geoprocessing.ExecuteToolAsync. These run off the MCT: the Pro API
    /// they call does its own marshalling, and awaiting inside QueuedTask
    /// would deadlock.
    /// </summary>
    public delegate Task<object> AsyncCommandHandler(Params parameters);

    /// <summary>
    /// Looks up a command and runs it where it is allowed to touch the project.
    ///
    /// ArcGIS Pro's object model may only be used on the Main CIM Thread, so
    /// everything is handed to QueuedTask.Run. Unlike the Python bridge this
    /// costs nothing in latency: Pro services the MCT queue continuously.
    ///
    /// Commands this add-in does not implement are forwarded to the Python
    /// bridge, which keeps arcpy -- and execute_arcpy_code in particular --
    /// available as an escape hatch.
    /// </summary>
    internal static class CommandRouter
    {
        private sealed class Registration
        {
            public string Name;
            public string Group;
            public string Summary;
            public CommandHandler Handler;
            public AsyncCommandHandler AsyncHandler;
            public bool RunOnMct;
        }

        private static readonly Dictionary<string, Registration> Commands =
            new Dictionary<string, Registration>(StringComparer.OrdinalIgnoreCase);

        private static readonly HashSet<string> Allowed = new HashSet<string>(
            new string[] { "ping", "get_capabilities", "diagnose", "get_arcgis_info", "get_project_info", "list_maps", "get_layers", "get_layer_info", "get_broken_layers", "activate_map", "get_map_view", "set_map_view", "export_map_view", "set_layer_visibility", "set_layer_transparency", "rename_layer", "set_definition_query", "get_map_extent", "list_layouts", "get_layout_info", "set_map_frame_extent", "set_layout_element", "activate_layout", "get_raster_palette", "set_raster_palette", "export_layout", "preview_layout", "save_project", "list_geoprocessing_tools", "describe_geoprocessing_tool", "list_toolboxes", "run_geoprocessing_tool", "check_extension", "get_messages" }, StringComparer.OrdinalIgnoreCase);
        public static int Count => Commands.Keys.Count(k => Allowed.Contains(k));


        public static void Register(string name, string group, string summary,
                                    CommandHandler handler, bool runOnMct = true)
        {
            Commands[name] = new Registration
            {
                Name = name,
                Group = group,
                Summary = summary,
                Handler = handler,
                RunOnMct = runOnMct,
            };
        }

        public static void RegisterAsync(string name, string group, string summary,
                                         AsyncCommandHandler handler)
        {
            Commands[name] = new Registration
            {
                Name = name,
                Group = group,
                Summary = summary,
                AsyncHandler = handler,
                RunOnMct = false,
            };
        }

        public static bool Knows(string command)
        {
            return command != null && Commands.ContainsKey(command);
        }

        public static async Task<object> DispatchAsync(string command, Params parameters,
                                                       JsonElement rawParameters)
        {
            if (string.IsNullOrWhiteSpace(command))
                throw new ArgumentException("No command given.");

            if (!Allowed.Contains(command))
                throw new InvalidOperationException("LOCAL_PROFILE_DISABLED: command is not enabled in the Pro 3.4.3 offline profile.");
            if (!Commands.TryGetValue(command, out var registration))
            {
                // Not ours -- let the Python bridge try. That is where arcpy,
                // and anything not yet ported, still lives.
                throw new InvalidOperationException("NO_PYTHON_FALLBACK: this command has no verified native handler.");
            }

            if (registration.AsyncHandler != null)
                return await registration.AsyncHandler(parameters).ConfigureAwait(false);

            if (!registration.RunOnMct)
                return registration.Handler(parameters);

            return await QueuedTask.Run(() => registration.Handler(parameters))
                .ConfigureAwait(false);
        }

        /// <summary>Everything this bridge can do, grouped -- for get_capabilities.</summary>
        public static object Describe()
        {
            var groups = Commands.Values.Where(c => Allowed.Contains(c.Name))
                .GroupBy(c => c.Group)
                .OrderBy(g => g.Key, StringComparer.Ordinal)
                .ToDictionary(
                    g => g.Key,
                    g => (object)g.OrderBy(c => c.Name, StringComparer.Ordinal)
                                  .Select(c => new Dictionary<string, object>
                                  {
                                      ["command"] = c.Name,
                                      ["summary"] = c.Summary,
                                  })
                                  .ToList());

            return new Dictionary<string, object>
            {
                ["implemented_by"] = "ArcGIS Pro add-in (C#)",
                ["command_count"] = Count,
                ["groups"] = groups,
                ["fallback"] = "disabled in local profile",
            };
        }
    }
}
