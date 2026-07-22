# Query tabs own the Workbench view

**Status:** accepted

The fixed Query tab strip is the product-level workspace container for both search contexts and the singleton Workbench context, shared by Desktop and PWA. Workbench keeps its draft and transient view state while inactive; `/workbench/` remains a deep link, tab switches replace the URL without adding browser history, and inactive searches/candidate scans are cancelled to keep the active workspace responsive.
