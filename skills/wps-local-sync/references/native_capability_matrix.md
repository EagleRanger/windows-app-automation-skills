# WPS native background capability matrix

Updated: 2026-08-22

## Conclusion

WPS cannot be treated as one completely headless, fully callable API surface. The local desktop object model is broad and suitable for many deterministic document operations, but coverage must be accepted per operation. UI commands, account/cloud services, Lingxi, and some declared COM members are separate execution domains.

## Local desktop COM

Read-only enumeration of the installed 12.1.0.28043 type libraries found:

| Component | Published types | Published interface-member entries | Local registration | Accepted background scope |
|---|---:|---:|---|---|
| Writer | 765 | 9,087 | `KWPS.Application` | prior read/view/export scope plus explicit text insertion, paragraphs, headers/footers, comments, bookmarks, and tracked-change state; replace/merge/table insertion quarantined |
| Calc | 1,041 | 17,559 | `KET.Application` | prior cells/formulas/chart/data scope plus sheet add/rename, rectangular writes, row/column insert, clear, filter state, and chart listing |
| Impress | 426 | 4,366 | `KWPP.Application` | prior slide/text/image/export scope plus duplicate/move/import, shape-level text/geometry, image replacement, notes, and slide image export; transition setting quarantined |
| PDF | 50 | 755 | `KPDF.Application` | info only; hidden native probe timed out and mutations opened visible WPS UI, so mutations are preblocked |

Member-entry counts describe the published type libraries; they are not counts of independently verified features. The declarations include broad objects such as comments, revisions, mail merge, formulas, charts, pivot tables, shapes, slide shows, PDF pages, annotations, search, security, printing, and export.

Use explicit adapters instead of a generic arbitrary-COM endpoint. For every new member path, verify its arguments and return values against the installed WPS build, test it on an isolated file, and require close/reopen effect evidence.

### Usually suitable for background adapters

- File open/save/save-as/export with explicit absolute paths.
- Document text, paragraphs, ranges, styles, tables, headers/footers, fields, comments, and tracked-revision data when individually verified.
- Worksheet cells, ranges, formulas, formats, sheets, charts, and data objects when individually verified and external refresh is disabled unless authorized.
- Presentation slides, shapes, text, page setup, images, and fixed-format export when individually verified.

## 2026-08-21 real-host coverage result

The accepted repair run executed 75 isolated cases. Seventy passed as written; two additional cases were test-oracle mistakes and were separately confirmed (`impress` replay text exists, and batch continue-on-error intentionally exits zero). Three Writer mutations failed material close/reopen acceptance:

- `writer replace` reported one replacement but the SHA-256 and reopened body were unchanged.
- `writer merge` could not replace the placeholder because the preceding replacement did not persist.
- `writer table-insert` changed the file but did not produce a separately addressable second table after reopen.

These three direct commands and the same commands embedded in `batch` now return `WPS_WRITER_MUTATION_UNVERIFIED` before WPS starts. WPS PDF mutation commands return `WPS_PDF_UI_REQUIRED` before WPS starts. This prevents the two observed failure classes: false success and unexpected foreground UI.

The baseline local regression suite passed 353 tests. The timeout path returned exit 60 after five seconds and left no shim process. The final host audit showed zero automation processes and zero visible WPS windows. WPS-exported Writer PDF (one A4 page) and Impress PDF (two 16:9 pages) were structurally reopened and visually rendered without blank pages, clipping, overlaps, or broken Chinese glyphs.

## 2026-08-22 capability expansion

The current `lc2panda/wps-skills` source was inventoried before porting. Its source registers 238 explicit `wps_*` tools; README totals include additional MCP built-ins and have drifted across revisions. Tool count is discovery evidence only, not host acceptance.

Real WPS tests accepted 30 new explicit adapter commands across Writer (11), Calc (9), and Impress (10). Every accepted mutation used an isolated copy, changed the intended structure, closed, reopened in a separate WPS invocation, and was independently read back. The presentation image export also produced and visually reopened a nonblank 1280x720 PNG. All three runs ended with zero automation processes and zero visible WPS windows.

`impress transition-set` returned success but reopened with WPS defaults (`Effect=0`, `Duration=0.5`), so direct and batch forms now fail closed with `WPS_IMPRESS_TRANSITION_UNVERIFIED`. Rectangular Calc writes run the same formula-injection guard as single-cell writes. The expanded full regression suite passes 367 tests.

### Not inherently headless

- `Dialogs`, `FileDialog`, print preview, slideshow playback, task panes, web dialogs, ribbon commands, login, payment/member prompts, and other features whose result is a window.
- Commands that depend on the active selection, foreground window, clipboard, current printer, add-in UI, or user confirmation.
- Macros and `Application.Run`: technically exposed, but they add document-code and trust-boundary risk and require task-specific authorization and inspection.

## WPS JavaScript add-ins

Official WPS documentation says add-ins can perform nearly all mouse/keyboard document operations, but an add-in is a Chromium page loaded inside a running WPS client. Browser integration through `WpsInvoke.InvokeAsHttp` starts WPS, is asynchronous, and requires the user to allow the launch. Therefore it is a high-coverage in-client route, not a pure unattended background service.

Use an add-in only when a needed native feature is not stable through COM and the benefit justifies installation, signing/deployment, WPS client startup, and a narrower authenticated local bridge. Do not install an add-in that exposes arbitrary local-file or clipboard access through permissive CORS.

## WPS 365 OpenAPI, WebOffice, and MCP

These are cloud/business integration surfaces, not direct control of the user's local WPS desktop session:

- WPS 365 OpenAPI covers cloud documents, contacts, messages, meetings, calendars, intelligent documents, and related enterprise services.
- Calls require an application, requested scopes, access tokens, and often enterprise or user authorization.
- Official WPS MCP is based on WPS 365 OpenAPI and currently requires trial/application access.
- WebOffice JSSDK operates on an initialized online document instance and requires a WebOffice application and callback service.

Keep cloud access as an opt-in connector with separate credentials, permission review, and data-boundary approval. It must not silently replace offline local processing.

## Lingxi and WPS AI

The installed build contains `wpslingxi.exe`, `kwpslingxi.dll`, and a Lingxi dock-panel component, but no Lingxi COM ProgID was registered and no official public local Lingxi API was found in the WPS developer documentation reviewed on 2026-08-21. Officially documented AI-facing surfaces are WPS 365 Agentspace, AI document services, web components, and OpenAPI endpoints; they require cloud application authorization.

Do not reverse-engineer or call private Lingxi IPC as a production route. If the user explicitly wants Lingxi itself, use the bounded visible-UI path or a separately authorized official cloud capability.

## Capability states

- `verified_background`: isolated write, save, close, separate reopen/read, validation, and cleanup passed.
- `declared_unverified`: present in an official API or local type library but lacks real host evidence.
- `ui_required`: the intended effect is inherently interactive or the background path is not reliable.
- `cloud_authorized`: requires network, app credentials, scopes, and user/enterprise authorization.
- `blocked`: reproducibly fails, times out, or leaves indeterminate state on the current build.

Never collapse these states into a single claim that “WPS is fully controllable.”

## Official references

- WPS add-in overview: https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/wps-integration-mode/wps-addin-development/addin-overview
- WPS add-in development and `InvokeAsHttp`: https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/wps-integration-mode/wps-addin-development/wps-addin-development-instructions
- WPS Writer Application object: https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/jsapi/wps/Application/obj
- WPS Calc Application object: https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/jsapi/et/Application/obj
- WPS Impress Application object: https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/jsapi/wpp/Application/obj
- WPS 365 Open Platform: https://open.wps.cn/documents/app-integration-dev/guide/overview
- WPS MCP introduction: https://open.wps.cn/documents/app-integration-dev/mcp-server/introduction
- WebOffice JSSDK overview: https://open.wps.cn/documents/app-integration-dev/docs-center/online-preview-edit/client/summary
- Agentspace chat API: https://open.wps.cn/documents/app-integration-dev/wps365/server/agentspace/chat/chat-create
