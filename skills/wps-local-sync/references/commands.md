# WPS bridge commands

Use the installed Skill wrapper. Run it from Codex in the actual Windows user context (`require_escalated`). Pass arguments as an array so Chinese paths and JSON remain intact.

```powershell
$bridge = Join-Path $env:USERPROFILE '.codex\skills\wps-local-sync\scripts\invoke_wps_cli.ps1'
```

## Writer examples

Read metadata:

```powershell
& $bridge -CommandArgs @('writer', 'info', 'C:\absolute\file.docx', '--json')
```

Read structure or body:

```powershell
& $bridge -CommandArgs @('writer', 'view', 'C:\absolute\file.docx', 'summary', '--json')
& $bridge -CommandArgs @('writer', 'get', 'C:\absolute\file.docx', '/body', '--json')
```

`writer replace`, `writer merge`, and `writer table-insert` are intentionally blocked by the installed wrapper on WPS 12.1.0.28043. They returned success without reliable close/reopen persistence, or inserted at an ambiguous location in an existing table document. Use the document artifact skill for those mutations, then reopen the result through WPS.

Existing table content can still be read:

```powershell
& $bridge -CommandArgs @('writer', 'table-get', 'C:\absolute\file_WPS工作副本.docx', '--index', '1', '--json')
```

The following Writer adapters passed real WPS save-close-reopen-read tests:

```powershell
& $bridge -CommandArgs @('writer', 'paragraph-list', 'C:\absolute\file_WPS工作副本.docx', '--json')
& $bridge -CommandArgs @('writer', 'text-insert', 'C:\absolute\file_WPS工作副本.docx', '--position', 'end', '--text', '新增内容', '--json')
& $bridge -CommandArgs @('writer', 'header-set', 'C:\absolute\file_WPS工作副本.docx', '--text', '页眉', '--json')
& $bridge -CommandArgs @('writer', 'comment-add', 'C:\absolute\file_WPS工作副本.docx', '--start', '0', '--end', '2', '--text', '批注', '--json')
& $bridge -CommandArgs @('writer', 'bookmark-list', 'C:\absolute\file_WPS工作副本.docx', '--json')
& $bridge -CommandArgs @('writer', 'track-changes-get', 'C:\absolute\file_WPS工作副本.docx', '--json')
```

Validate and export:

```powershell
& $bridge -CommandArgs @('writer', 'validate', 'C:\absolute\file_WPS工作副本.docx', '--json')
& $bridge -CommandArgs @('writer', 'export-pdf', 'C:\absolute\file_WPS工作副本.docx', '--output', 'C:\absolute\file_WPS工作副本.pdf', '--json')
```

## Calc and Impress examples

Different-component commands may run in separate workers concurrently on distinct paths. Current production-wrapper overlap acceptance covers Calc + Impress; other cross-type pairings require the scoped first-use check described in `parallel_sessions.md`. Do not use `-AllowVisibleWps` to bypass a foreign-session check; do not invoke legacy same-component CLI calls concurrently against a shared PPT session.

The following Calc and Impress paths are verified locally. Inspect the exact operation before using a broader command:

```powershell
& $bridge -CommandArgs @('calc', 'cell-set', 'C:\absolute\book_WPS工作副本.xlsx', 'A1', '已写入', '--json')
& $bridge -CommandArgs @('calc', 'cell-get', 'C:\absolute\book_WPS工作副本.xlsx', 'A1', '--json')
& $bridge -CommandArgs @('calc', 'range-set', 'C:\absolute\book_WPS工作副本.xlsx', 'A1:B2', '--data', '[[1,2],[3,4]]', '--json')
& $bridge -CommandArgs @('calc', 'sheet-add', 'C:\absolute\book_WPS工作副本.xlsx', '--name', '新工作表', '--json')
& $bridge -CommandArgs @('calc', 'auto-filter-status', 'C:\absolute\book_WPS工作副本.xlsx', '--sheet', '新工作表', '--json')
& $bridge -CommandArgs @('calc', 'chart-list', 'C:\absolute\book_WPS工作副本.xlsx', '--sheet', '新工作表', '--json')
& $bridge -CommandArgs @('impress', 'slide-add', 'C:\absolute\deck_WPS工作副本.pptx', '--layout', '1', '--title', '已写入', '--json')
& $bridge -CommandArgs @('impress', 'text-get', 'C:\absolute\deck_WPS工作副本.pptx', '--slide', '1', '--json')
& $bridge -CommandArgs @('impress', 'shape-list', 'C:\absolute\deck_WPS工作副本.pptx', '--slide', '1', '--json')
& $bridge -CommandArgs @('impress', 'slide-duplicate', 'C:\absolute\deck_WPS工作副本.pptx', '--slide', '1', '--json')
& $bridge -CommandArgs @('impress', 'notes-get', 'C:\absolute\deck_WPS工作副本.pptx', '--slide', '1', '--json')
& $bridge -CommandArgs @('impress', 'slide-export-image', 'C:\absolute\deck_WPS工作副本.pptx', '--slide', '1', '--output', 'C:\absolute\slide1.png', '--json')
```

`impress transition-set` is preblocked with `WPS_IMPRESS_TRANSITION_UNVERIFIED`: WPS accepted the call but restored its default transition after close/reopen.

For each new format, first use an isolated fixture and require write, save, close, reopen, and read evidence.

PDF `merge`, `extract-pages`, `split`, and `watermark` are preblocked because this WPS build opens a visible PDF reader. `pdf info` remains safe; use the PDF artifact skill for PDF mutations.

## Wrapper results

- Exit 20 / `VISIBLE_WPS_WINDOW`: a visible user WPS session exists; do not force background COM.
- Exit 60 / `WPS_COM_TIMEOUT`: the call timed out and the wrapper cleaned only automation processes started after its baseline.
- Exit 31 / `WPS_WRITER_MUTATION_UNVERIFIED`: a Writer mutation with failed close/reopen evidence was quarantined before WPS launch.
- Exit 32 / `WPS_IMPRESS_TRANSITION_UNVERIFIED`: a presentation transition that failed close/reopen persistence was quarantined before WPS launch.
- Exit 30 / `WPS_PDF_UI_REQUIRED`: a PDF mutation known to open visible WPS UI was quarantined before launch.
- Nonzero CLI exit: treat the file as indeterminate until its hash, modification time, and reopen state are checked.
