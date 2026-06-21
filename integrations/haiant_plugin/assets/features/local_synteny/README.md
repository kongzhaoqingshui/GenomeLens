# gljcvi-local-synteny assets

This lightweight plugin corresponds to the ``analyze mcscan jcvi local_synteny`` automatic flow.

It writes ``output/genomelens_request.json`` with ``workflow = local_synteny`` and then calls:

```powershell
gljcvimcscan\genomelens.cmd analyze run output\genomelens_request.json
```

If ``species`` is not provided in ``params.json``, the plugin mirrors the CLI auto-directory behavior and discovers paired species files from ``input_dir``.

Contents:

- ``config.json``: HAIant form metadata for the local synteny entry. All optional parameters exposed by the ``analyze mcscan jcvi`` automatic flow are included.
- ``params.json``: runnable sample parameters using the packaged ``input/`` files.
- ``README.md``: packaging notes for maintainers.

The package does not carry a runtime or toolchain. Install ``gljcvimcscan`` beside this plugin or set ``GLJCVIMCSCAN_HOME``.
