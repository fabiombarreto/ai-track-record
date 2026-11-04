# DuckDB

- **Version used:** 2.0.0 (`harness/uv.lock`), the harness's only declared dependency.
- **Docs:** https://duckdb.org/docs (Context7 ids `/duckdb/duckdb-python`, `/websites/duckdb_current`).

## Use in this project

- `atr.store.load` rebuilds `~/atr/data/atr.duckdb` from scratch on every run: tables for trials, model usage, events, metric points, review findings and protocol steps, plus views such as the reconciliation and spend.
- `atr.store.export` opens the database read-only and copies allowlisted fields.

## Patterns from the docs

- `duckdb.connect(path, read_only=True)` for readers; a read-only connection cannot write.
- `con.execute(query, params)` with `?` parameters, then `.description` for column names and `.fetchall()` for rows.
- `con.sql(...)` returns a relation that can be queried further or printed.

## Gotchas

- `JSON` is an alias of `VARCHAR`: fetched JSON columns come back as Python `str` and must be parsed.
- A database file held open by a writer cannot be opened by another process; close the loader before running exports or ad-hoc queries.
