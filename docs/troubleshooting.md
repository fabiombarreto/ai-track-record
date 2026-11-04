# Troubleshooting

| Symptom | Cause | What to do |
|---|---|---|
| A run fails before its agent makes any API call | Docker Desktop lost its network, or another infrastructure problem | It is an `error` outcome: set it aside and run it again (the launcher does this up to three times) |
| A resumed job runs a trial beside an old one | A killed job left its Compose projects | `python -m atr.ops.cleanup <job dir>` before `harbor job resume` |
| A Target A service is unreachable by name in a run | Harbor's allowlist routes Compose services through its egress sidecar | Point the app at `127.0.0.1`, as Target A's templates do |
| Telemetry events out of order | The WSL clock jumped during the run | Order by `event.sequence`, as the loader does |
| Output tokens missing from telemetry metrics on older runs | Requests over about 60 seconds lost their last metric batch before M3's fix | Use the events and the SDK's usage; the shortfall is recorded, not corrected |
| A batch stops with a usage-limit error | The API workspace reached its monthly limit | Wait for the next allowance; set `ALLOW_USD` for the batch |
| A `wsl.exe` command loses its quoting or PATH | `--` or a leading `/` in the command string | Use `wsl.exe -d Ubuntu --exec bash -lc '...'` and never start the string with `/` |
| C: runs out of space | The WSL and Docker disks grow on C: | Keep large files, such as model weights, on D: |
| The local server does not fit in VRAM | The Windows desktop uses about 2 GB of the GPU | Move the display to the integrated graphics or close GPU apps; lower `--n-cpu-moe` layers on the GPU |
| `atr.local.serve start` stops with "key check failed" | The server accepted a request without its key, or rejected the key | Check `api_key_env` in `models.toml` against the image's `--help` |
| `atr.local.serve start` says the weights are not verified | The file is missing, incomplete, or has no marker | Run `python -m atr.local.fetch <id>` |
