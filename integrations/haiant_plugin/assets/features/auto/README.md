# gljcvi-auto assets

This lightweight HAIant plugin corresponds to the ``analyze mcscan jcvi`` one-click auto flow.

Instead of building a ``genomelens_request.json`` and calling ``analyze run``, it dynamically
constructs ``output/jcvi.config.json`` from the plugin parameters and directly invokes the
external GenomeLens executable:

```powershell
<genomelens_exe> analyze mcscan jcvi <input_dir> <output_dir> <output\jcvi.config.json>
```

The path to ``<genomelens_exe>`` is read from ``params.json`` (``genomelens_exe`` or ``GenomeLens_Path``) or from the ``GENOMELENS_EXE`` environment variable. If the executable points to a ``.cmd`` / ``.bat`` file, the plugin transparently dispatches it through ``cmd.exe /c``.

When ``target_gene_ids`` is provided, the generated ``jcvi.config.json`` switches the workflow to ``local_synteny``; otherwise it stays in ``graphics_synteny``.

After the external GenomeLens process exits, the plugin automatically packs everything in ``output_dir`` except the ``results`` directory into ``output/intermediates.zip`` and writes ``output/intermediates.zip.deletable`` as a marker.  The original intermediate files are removed after archiving, leaving only ``results/``, the archive, and the marker in the output root.

Contents:

- ``config.json``: HAIant form metadata for the unified MCscan auto entry. Parameters exposed by the ``analyze mcscan jcvi`` auto flow are included.
- ``params.json``: runnable sample parameters using an ``input/`` directory of paired species files.
- ``README.md``: packaging notes for maintainers.

The package does not carry the GenomeLens runtime or toolchain. Install GenomeLens separately and provide its executable path.
