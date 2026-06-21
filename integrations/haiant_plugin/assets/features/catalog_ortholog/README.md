# gljcvi-catalog-ortholog assets

This lightweight plugin writes `output/genomelens_request.json` with `workflow = catalog_ortholog` and then calls:

```powershell
gljcvimcscan\genomelens.cmd analyze run output\genomelens_request.json
```

Contents:

- `config.json`: HAIant form metadata for the catalog_ortholog entry.
- `params.json`: runnable sample parameters using the packaged `input/` files.
- `README.md`: packaging notes for maintainers.

The package does not carry a runtime or toolchain. Install `gljcvimcscan` beside this plugin or set `GLJCVIMCSCAN_HOME`.
