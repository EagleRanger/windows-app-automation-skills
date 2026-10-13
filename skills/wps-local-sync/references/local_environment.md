# Local WPS environment

Updated: 2026-10-12

Current concurrency acceptance uses WPS **12.1.0.28802 (32-bit)**. The older feature coverage below remains its dated evidence, not a claim that all 75 cases were rerun on the current build. See [parallel_sessions.md](parallel_sessions.md) for current per-resource admission and cleanup rules.

## Verified host

- WPS Office: `C:\Program Files (x86)\Kingsoft\WPS Office\12.1.0.28043\office6\wps.exe`
- WPS version: 12.1.0.28043
- WPS bitness: 32-bit
- Local bridge root: set `WPS_LOCAL_AI_HOME` to a compatible checkout of the WPS local automation project.
- Upstream base: `lewis-hui1202/wps-cli` commit `2087ed3bb6c41331bb31ef15ea9d0aa241236d1f`
- Accepted local compatibility commit: `9bb0e8642da91c59af95230e821f9fb83bf4a2ee`
- Accepted capability-expansion commit: `0bf8fbe8475a35cab30f06fd40f9b1aa78937f36` on local branch `wps-capability-expansion-20260822`
- Isolated executable: `$env:WPS_LOCAL_AI_HOME\.venv\Scripts\wps.exe`
- Published native libraries: `wpsapi.dll`, `etapi.dll`, `wppapi.dll`, `pdfapi.dll` plus their JS bindings.

## COM registration boundary

`wps doctor --fix` registered `KWPS.Application` successfully in the actual Windows user context. The restricted Codex process has a different registry view and can still report no ProgID. Therefore run local WPS bridge calls with host-user elevation; do not treat the restricted probe as current host truth.

On 2026-08-22 a restricted Calc call again reported all ProgIDs missing. Repeating the same isolated test in the actual Windows user context passed all nine Calc checks, and follow-up Writer and Impress reads also passed. This confirms that a restricted negative probe must not trigger repeated registration repair; test the host-user route first.

## Local compatibility patches

The pinned fork contains narrow WPS 12.x patches:

1. Writer table insertion returns `doc.Tables.Count` because the WPS table COM object does not expose Microsoft Word's `Table.Index` property. Real testing later showed insertion into an existing table document was still position-ambiguous, so the production wrapper quarantines the command.
2. Session teardown closes files in the admitted automation instance without saving before `app.Quit()`. Admission now uses `DispatchEx` and rejects populated or visible returned sessions before mutation. Do not attach this teardown to a shared multi-PPT session.
3. WPS Presentation may omit `Application.Quit`; teardown accepts that after closing presentations. The wrapper no longer reaps a global new-process difference; ambiguous leftovers require exact ownership reconciliation.
4. WPS title-slide layouts expose the centered title as placeholder type 3 and subtitle as type 4. The fork recognizes both regular and centered title placeholders, and raises an error instead of reporting success when a requested placeholder was not found.
5. Calc conditional formatting re-reads the new condition from the WPS collection instead of trusting the late-bound `Add` return object; listing/deletion use the used-range collection.
6. Calc data-validation listing scans the bounded used range because WPS does not expose worksheet validation as a normal enumerable collection. Pivot refresh accepts WPS's callable `PivotCaches` accessor.
7. Impress dump replay creates blank slides and reconstructs text, pictures, and tables rather than silently writing a zero-slide deck.
8. Explicit Writer adapters use document ranges for insertion and expose paragraphs, headers/footers, comments, bookmarks, and tracked-change state.
9. Explicit Calc adapters expose safe rectangular writes, sheet add/rename, row/column insertion, content clearing, auto-filter state, and chart listing. Rectangular writes reject formula-like input unless the dedicated formula command is used.
10. Explicit Impress adapters expose slide duplicate/move/import, shape-level text/geometry, image replacement, notes, and slide image export. Transition mutation remains quarantined after a real persistence failure.

The historical blanket visible-window veto is superseded: independent components may overlap. The wrapper uses component/file leases; the backend protects the actual returned COM session. See `parallel_sessions.md` for verified scope and same-component limits.

## Verified coverage scope

- DOCX: create, table write, hash change, separate reopen and table read, native validation.
- XLSX: create, `A1` write, separate reopen and cell read, native validation.
- PPTX: create, title-slide add, centered-title write, separate reopen and text read, native validation.
- All three postchecks observed zero remaining automation processes and zero visible WPS windows.
- Writer-to-PDF export passed. Native `KPDF.Application` is registered and its type library is readable, but the hidden open/read probe timed out and is currently blocked for production use.
- The 75-case real-host repair run accepted Calc cells/formulas/sort/chart/conditional-format/data-validation/sparkline/refresh/CSV, Impress slide/text/image/delete/refresh/export and replay text, Writer read/view/image/page setup/style/refresh/validation/export, mixed batch behavior, error paths, timeout cleanup, and PDF foreground preblocking.
- `writer replace`, `writer merge`, and `writer table-insert` failed material close/reopen acceptance and are quarantined both directly and when nested in batch JSON.
- PDF mutations opened a visible WPS PDF reader in the first run. The exact test window was identified by path and closed; the wrapper now blocks those commands before launch.
- The 2026-08-22 expansion accepted 30 additional real-host adapters: Writer 11, Calc 9, Impress 10. `impress transition-set` was the one tested candidate quarantined after WPS restored defaults on reopen.
- Full regression: 367 tests passed. Final expansion process audits: zero new automation processes and zero visible WPS windows.

These smoke tests prove the named minimal paths only. Layout-sensitive or complex production artifacts still require format-specific rendering and visual inspection.

## Rejected default route

The downloaded `WPS-AI` add-in was retained only for comparison. Its local proxy exposes clipboard and local-file operations behind a permissive browser-facing surface, so it is not installed unchanged. The current production route is the smaller local COM CLI plus the guarded wrapper.
