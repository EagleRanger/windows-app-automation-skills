# Multiple WPS files and component isolation

Validated 2026-10-12 on Windows, WPS 12.1.0.28802 (32-bit). This narrows the historical blanket single-WPS restriction; it does not validate every command on the new build.

## Route by the actual shared resource

- Calc + Impress, Writer + Calc, or Writer + Impress: separate component sessions and distinct input/output paths are eligible for background overlap. **Calc + Impress has current real overlap, both close orders, continued writing after peer shutdown, and independent reopen evidence.** Other cross-type combinations rely on separate component tests and require a small scoped acceptance test when first used together.
- The production wrapper leases each requested component plus recognized absolute input/output paths, including cross-component PDF outputs. A batch leases all its component types; unknown commands conservatively lease all three. A busy lease returns `WPS_RESOURCE_BUSY` naming the actual resource, not a claim that the whole desktop is busy.
- Writer and Calc `DispatchEx` created distinct COM servers in the two-file tests. The CLI still uses component leases to keep its active-document/session teardown behavior predictable.
- Impress `DispatchEx` reused one COM session. Two workers each binding their own Presentation passed 20 write/save/readback rounds, peer close, continued writing and independent reopen. This proves multiple-file content work, not independent COM processes or parallel CPU execution.

## Explicit-object PPT route

For two PPTs in one owned session, bind each returned `Presentation` and operate on `pres.Slides`, never `ActivePresentation`, global Selection, or active-window state. Keep one shared-session owner and per-file write ownership. Close only the owned Presentation; do not call `Application.Quit`, hide the application, change application-wide options, or run legacy CLI teardown while a peer file exists. On final close, this WPS build may exit the server automatically; an RPC error is not accepted until Close returned, no peer remains, and saved files pass reopen/read.

The test harness is project evidence, not a general arbitrary-action runner: `research/multiwindow_20261012/test_parallel.py --shared` with `impress` as its positional component. Production tasks must fix exact target copies, permitted operations, output paths, and reopen/visual acceptance in their own task contract.

## No blanket window veto or broad process kill

The updated backend checks the **returned COM object** before mutation: document count must be zero and Visible false. A populated or visible object fails as `WPS_FOREIGN_SESSION`; no harden/hide/Quit occurs and there is no fallback attach attempt. This protects a shared PPT session while allowing an independent Calc call to finish; the live sentinel test confirmed the held PPT remained intact.

Normal teardown belongs to the admitted session. The wrapper never kills WPS merely because its PID appeared after another job's baseline. On timeout it terminates only its CLI and reports observed process IDs as non-authoritative clues. Reconcile exact ownership before any WPS cleanup; timeout cleanup is deliberately not presented as complete.

## Official WpsClient route: investigation only

[Official documentation](https://open.wps.cn/documents/app-integration-dev/wps365/client/wpsoffice/wps-integration-mode/wps-addin-development/wps-addin-integration-business-system-development) defines per-client routing, silent start, and close. Actual local relay version was 1.0.3. Two silent PPT starts produced distinct client IDs and matching `/wpsjsclient /nosurface` processes, but application calls returned `No Plugin named...`. Minimal temporary publish deployment then timed out; an Origin-bearing transport attempt returned HTTP 503. No fixture file I/O passed through that route. The Node browser-transport adapter is an additional evidence limitation; this does not establish that an ordinary supported browser or another WPS edition would fail.

Temporary registrations were disabled where the API responded; the two config files containing only this test's entries were moved to the research cleanup archive, restoring their prior absence. Exact test-owned no-surface processes and the test relay were stopped. No cloud account, user document, or unmodified third-party add-in was used. Do not promote this official route into production or weaken host deployment controls on these results.

## Evidence pointers

- `.project-reasoning/runs/WPS-MULTIWINDOW-20261012.md`: original two-file tests and REA limitations.
- `.project-reasoning/runs/WPS-CROSS-TYPE-20261012.md`: cross-type acceptance, production promotion, negative guards, and official route boundary.
- `research/multiwindow_20261012/mixed_calc_impress_012206/receipt.json`
- `research/multiwindow_20261012/mixed_impress_calc_012213/receipt.json`
- `research/multiwindow_20261012/bridge_mixed_013351/receipt.json`
- `research/multiwindow_20261012/bridge_mixed_014052/receipt.json`: installed-wrapper cross-type re-acceptance, 120/120 batch substeps, about 3.900 seconds observed overlap.
- `research/multiwindow_20261012/admission_live_013542/receipt.json`
