# gljcvi-auto assets

This lightweight HAIant plugin provides a unified entry point for the ``analyze mcscan jcvi`` automatic flow.

It writes ``output/genomelens_request.json`` with the ``workflow`` selected in ``params.json`` and then calls the external GenomeLens executable:

```powershell
<genomelens_exe> analyze run output\genomelens_request.json
```

The path to ``<genomelens_exe>`` is read from ``params.json`` (`genomelens_exe`) or from the ``GENOMELENS_EXE`` environment variable. If ``genomelens_exe`` points to a ``.cmd`` / ``.bat`` file, the plugin transparently dispatches it through ``cmd.exe /c``.

Supported workflows (set via ``workflow``):

- ``graphics_synteny`` — pairwise synteny figure
- ``graphics_dotplot`` — pairwise dotplot
- ``graphics_karyotype`` — pairwise karyotype figure
- ``catalog_ortholog`` — ortholog catalog
- ``local_synteny`` — target-gene-centered local synteny
- ``graphics_histogram`` — numeric histogram

Contents:

- ``config.json``: HAIant form metadata for the unified MCscan auto entry. All optional parameters exposed by the ``analyze mcscan jcvi`` automatic flow are included.
- ``params.json``: runnable sample parameters using an ``input/`` directory of paired species files.
- ``README.md``: packaging notes for maintainers.

The package does not carry the GenomeLens runtime or toolchain. Install GenomeLens separately and provide its executable path.
