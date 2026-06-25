# Upstream JCVI Source

- Upstream project: `https://github.com/tanghaibao/jcvi`
- Upstream license in use: `BSD-3-Clause`
- Local reference tree used during construction: `references/upstream/jcvi`
- Vendored runtime tree used by GenomeLens: `engines/jcvi/src/jcvi`
- Current vendored upstream version: `1.6.6`
- Current patchset name: `windows-genomelens`

## Git checkpoints in this repository

- `60915aa1`: initial vendored JCVI import into the GenomeLens repository
- `126ab6c5`: upgrade vendored JCVI from `1.6.5` to `1.6.6`

## Authorship note

This repository keeps the real GenomeLens import and maintenance history as Git commits by the GenomeLens team.
It does not rewrite Git author metadata to impersonate upstream JCVI authors.

Upstream authorship is instead preserved through:

- the upstream license file under `engines/jcvi/licenses/`
- the upstream project metadata in `references/upstream/jcvi/`
- the version and patchset metadata exposed by `jcvi_genomelens probe`

Any future direct edits to `engines/jcvi/src/jcvi/` must be recorded in both:

- `engines/jcvi/vendor/upstream-jcvi/patchset.md`
- `engines/jcvi/上游修改汇总.md`
