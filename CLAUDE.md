# CLAUDE.md — imdb-migrator

Python tool that migrates ratings and watchlists between two IMDB accounts
(automated browser login/export/import; credentials never stored). **Parked /
backup-only** — kept for reference, no active development.

## Stack / run
Python 3.7+ + Chrome. `pip install -r requirements.txt`, then
`./run_migration.sh` (or `python imdb_migration_script.py`). Tests:
`python test_imdb_migrator.py`.

## Conventions
- Canonical remote: Forgejo `cowie-creative/imdb-migrator` (git-ssh :2222);
  GitHub mirror `TuckerCowie/IMDB-Migrator`.
- Project ledger: `docs/product/status.yaml` (product-status/v1).
- House standards live in `~/Dev/agent-workflows` — follow them.
