# Third-party notices

## ArcGIS Pro local automation AddIn source

The source and notices under `skills/arcgis-pro-local-automation/assets/addin-source/` are distributed under their own GNU Affero General Public License v3 or later terms, with the additional Esri SDK linking exception stated in `NOTICE`. The full text is in `skills/arcgis-pro-local-automation/assets/addin-source/LICENSE`.

That component is:

> ArcGIS Pro MCP — Copyright (C) 2026 Pisut Nakmuenwai

This aggregation does not change that component's license, commercial licensing request, or source-conveyance obligations. ArcGIS Pro itself, the ArcGIS Pro SDK, and Esri trademarks are not redistributed.

## wps-cli vendor source

The vendored source under `skills/wps-report-workflow/vendor/wps-cli/` is retained under its MIT license in `skills/wps-report-workflow/vendor/wps-cli/LICENSE`.

The wps-cli resident-service code can create a short-lived local authorization token at runtime and keep it in the system temporary directory so its local client and daemon can authenticate. That behavior does not embed a credential in this package. Tokens and other credential-like runtime values remain local and must not be committed.

## Other bundled assets and dependencies

Application programs, SDKs, extensions, model weights, fonts, service terms, and online accounts are not included unless their source and license state otherwise. Each skill downloads only from addresses and package versions documented in its own references, and users must comply with the relevant vendor terms. Model weights and large dependencies are downloaded separately and verified before use.
