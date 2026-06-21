# gljcvimcscan Assets

- `config.json`: HAIant form metadata for the heavy-center `local_synteny` workflow.
- `params.json`: a runnable two-species example that targets `qgene2` in the reference species.
- This center entry always writes `output/genomelens_request.json` and then calls the same-directory platform shell:

```text
gljcvimcscan\genomelens.cmd analyze run output\genomelens_request.json
```

- `target_gene_ids` accepts either a comma-separated string or a JSON list.
