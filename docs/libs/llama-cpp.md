# llama.cpp server

- **Version used:** build b12063 (commit `2cbca38`), image `ghcr.io/ggml-org/llama.cpp:server-cuda-b12063`, CUDA 12.8, pinned by digest in `infra/local-inference/models.toml`.
- **Docs:** https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md (Context7 id `/ggml-org/llama.cpp`). The README follows `master`; check flags against the image's `--help`.

## Use in this project

- Serves one open-weight GGUF model for the local models plan; started and stopped by `atr.local.serve`, measured by `atr.local.bench`.
- Speaks Anthropic's Messages API (`POST /v1/messages`, `POST /v1/messages/count_tokens`) since January 2026, so Claude Code can point at it directly with `ANTHROPIC_BASE_URL`.

## Patterns from the docs

- API key from the `LLAMA_API_KEY` environment variable (or `--api-key`, `--api-key-file`); clients send it as a Bearer token.
- `--n-cpu-moe N` keeps the mixture-of-experts weights of the first N layers in RAM; `--n-gpu-layers` sets the layers in VRAM.
- `--chat-template-kwargs '<json>'` passes template options, such as `{"enable_thinking":true}` for Qwen models.
- `--cache-type-k/--cache-type-v` quantize the KV cache; `--flash-attn on|off|auto`.
- `--parallel N` sets the slots; with unified KV the context is shared across them.
- The native `POST /completion` returns `timings` (prompt and generation tokens and speeds); `cache_prompt: false` forces the whole prompt to be processed.
- `--metrics` enables the Prometheus endpoint; `/slots` shows per-slot state and sampling.

## Gotchas

- `--cache-ram` defaults to 8192 MiB of host RAM for the prompt cache, which this machine must budget; 0 disables it.
- `--mlock` is no longer a flag: it is `--load-mode mlock`.
- Prompt caching can make results nondeterministic.
- Some endpoints, such as model listing, may not require the key; check authentication on an endpoint that does, such as `count_tokens`.
- For Qwen3.6, Unsloth warns against CUDA 13.2 builds, which can produce garbled output.
