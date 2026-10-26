# ETHOS V1 Verification

The active project root is `linked/main`. Run the canonical V1 regression from
that directory:

```text
python3 -m unittest discover -v
```

It discovers every `test*.py` module in the active project root using the
standard-library runner. It intentionally excludes workspace archives,
duplicates, legacy projects, and `.venv` because they are not part of the
active implementation root. No tests are excluded within `linked/main`.

This command is canonical because the project uses `unittest.TestCase`,
including dynamically generated test methods. Pytest is not canonical: its
collection invokes two project `setup(directory)` helpers as pytest setup
hooks, and global plugin autoload is also environment-dependent.

The former 428-test checkpoint did not record its command, discovery root, or
dynamic-test accounting. Current artifacts contain 62 unique active test
modules and dynamically generated Sloth/runtime cases; no duplicate active
test filename is discovered. Without Git provenance, the precise historic
subset cannot be reconstructed truthfully. The canonical count is therefore
the result emitted by the command above, not a forced return to 428.
