# gljcvi-dotplot assets

This lightweight HAIant plugin corresponds to the ``analyze mcscan jcvi graphics_dotplot`` automatic flow.

It writes ``output/genomelens_request.json`` with ``workflow = graphics_dotplot`` and then calls the external GenomeLens executable:

```powershell
<genomelens_exe> analyze run output\genomelens_request.json
```

The path to ``<genomelens_exe>`` is read from ``params.json`` (`genomelens_exe`) or from the ``GENOMELENS_EXE`` environment variable. If ``genomelens_exe`` points to a ``.cmd`` / ``.bat`` file, the plugin transparently dispatches it through ``cmd.exe /c``.

Contents:

- ``config.json``: HAIant form metadata for the dotplot-only entry.
- ``params.json``: runnable sample parameters using an ``input/`` directory of paired species files.
- ``README.md``: packaging notes for maintainers.

The package does not carry the GenomeLens runtime or toolchain. Install GenomeLens separately and provide its executable path.
