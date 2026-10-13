# Verified Windows Photoshop route

## Proven host pattern

The locally verified host is Photoshop 2021 version 22.4.2. The stable sequence is:

1. Confirm a visible, responsive Photoshop process.
2. Attach to the running Photoshop.Application object through the Windows Running Object Table.
3. Execute bounded ExtendScript through DoJavaScript.
4. Verify the active document path and dimensions inside Photoshop immediately before mutation.
5. Save only to the authorized path, then close and reopen when the task requires save verification.

Do not let a bridge silently start Photoshop with automation or embedding flags. A process without a visible main window is not a usable editing session.

## Photoshop 2021 constraints

- The ExtendScript engine may not provide a global JSON object. Embed a previously validated object literal or ship a compatible parser; do not call JSON.parse without testing.
- LargeDocumentFormatSaveOptions is not constructible in this host. Save PSB with an ActionDescriptor whose format is largeDocumentFormat.
- A hidden parent group may become visible after reopening if that hidden group was the active layer at save time. Activate a stable visible layer first, then hide the parent group, save, close, and reopen.
- TextItem horizontalScale persists as an integer. Quantize the scale before calculating tracking, then use tracking to compensate remaining line-width error.

## Interrupted-call settlement

Long duplicate, resize, flatten, save, or reopen operations can outlive the calling shell. If the caller exits:

- Inspect the Photoshop window title, active document, document count, target file existence, and saved state.
- Do not submit the same write again while a named temporary document remains active.
- If the exact automation-created temporary document is the only unfinished object, close only that named temporary document without saving after confirming the original saved document remains available.
- Never force-terminate Photoshop as a shortcut.

## Evidence vocabulary

- connected: attached to the intended visible instance.
- readable: retrieved current document state.
- written: observed the requested layer or pixel mutation.
- saved: the authorized file exists and Photoshop reports a saved document.
- reopened: the saved file was closed and reopened with required structure intact.
- visually accepted: a rendered comparison or user inspection confirms the result, separately from structural checks.
