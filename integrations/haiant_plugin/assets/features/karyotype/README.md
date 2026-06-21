# gljcvi-karyotype assets

This lightweight plugin writes `output/genomelens_request.json` with `workflow = graphics_karyotype` and then calls:

```powershell
gljcvimcscan\genomelens.cmd analyze run output\genomelens_request.json
```

Contents:

- `config.json`: HAIant form metadata for the karyotype entry.
- `params.json`: runnable sample parameters using the packaged `input/` files.
- `README.md`: packaging notes for maintainers.

The package does not carry a runtime or toolchain. Install `gljcvimcscan` beside this plugin or set `GLJCVIMCSCAN_HOME`.
