# gljcvi-auto assets

This lightweight HAIant plugin corresponds to the ``analyze mcscan jcvi`` one-click auto flow.

It writes ``output/genomelens_request.json`` with ``workflow = graphics_synteny`` and then calls the external GenomeLens executable:

```powershell
<genomelens_exe> analyze run output\genomelens_request.json
```

The path to ``<genomelens_exe>`` is read from ``params.json`` (`genomelens_exe`) or from the ``GENOMELENS_EXE`` environment variable. If ``genomelens_exe`` points to a ``.cmd`` / ``.bat`` file, the plugin transparently dispatches it through ``cmd.exe /c``.

When ``target_gene_ids`` is provided, the platform automatically switches to the local synteny mode, matching the CLI behavior of ``analyze mcscan jcvi`` with ``--target-genes``.

Contents:

- ``config.json``: HAIant form metadata for the unified MCscan auto entry. All optional parameters exposed by the ``analyze mcscan jcvi`` auto flow are included.
- ``params.json``: runnable sample parameters using an ``input/`` directory of paired species files.
- ``README.md``: packaging notes for maintainers.

The package does not carry the GenomeLens runtime or toolchain. Install GenomeLens separately and provide its executable path.
