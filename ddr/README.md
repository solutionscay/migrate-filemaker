# DDR library

Real FileMaker DDR exports for developing and testing the skill. Everything in
this folder except this file is git-ignored. It is client data: never commit
it, never copy names or content from it into the repo, tests, or docs.

One folder per solution, one subfolder per export set. Each set holds the
FileMaker DDR XML files of one solution (one per FileMaker file) and its
`Summary.xml` when there is one.

```
ddr/
  <solution>/<set>/     the XML files of one export, plus Summary.xml when present
```

Add a new export as `ddr/<solution>/<set>/`. Explode a set with:

```bash
python3 scripts/explode_ddr.py ddr/<solution>/<set> /tmp/objects-<set>
```
