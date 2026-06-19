# Conclava v1.5 Handoff

## Status

This package is the **G10 Fusion Deliberation Router** build for Conclava v1.5.

Verified during G10:

```text
pytest tests/ -q -> 211 passed, 1 warning
LM Studio server -> http://127.0.0.1:1234/v1
Conclava gateway -> http://127.0.0.1:8088
ds4 -> http://127.0.0.1:8000/v1

# G10 new model ids exposed in /v1/models:
conclava-fusion            # OpenAI Chat + OpenAI Responses
claude-conclava-fusion     # Anthropic Messages

# G10 E2E scripts (all chmod +x):
bash scripts/test_fusion_quality.sh
bash scripts/test_fusion_budget.sh
bash scripts/test_fusion_coding.sh
bash scripts/test_fusion_heavy.sh    # requires ds4 up
bash scripts/test_fusion_custom.sh
bash scripts/test_fusion_bad_preset.sh
bash scripts/warmup_fusion_quality.sh
```

The G10 build adds an **OpenRouter-style multi-model deliberation router** on
top of the G09 LM Studio routing layer. Same routing surface for non-fusion
profiles, plus two new model ids that trigger the serial deliberation runner.

The v1.5 model plan uses specialization rather than replacement. Local non-ds4 profiles now use LM Studio model ids from `~/.lmstudio/hub/models`:

```text
MODEL_FAST=google/gemma-4-26b-a4b-qat
MODEL_CODER=qwen/qwen3-coder-next
MODEL_TOOLER=qwen/qwen3-coder-next
MODEL_CRITIC=deepseek-r1-distill-qwen-32b
MODEL_JUDGE=deepseek-r1-distill-qwen-32b
MODEL_FORMATTER=google/gemma-4-26b-a4b-qat
MODEL_VISION_FAST=google/gemma-4-26b-a4b-qat
MODEL_VISION_PRO=qwen/qwen3-vl-30b
MODEL_AGENTIC_PRO=qwen/qwen3.6-35b-a3b
MODEL_HERMES_PRO=qwen/qwen3.6-35b-a3b
MODEL_AGENTIC_MLX=qwen/qwen3.6-35b-a3b
MODEL_FORMATTER_MLX=google/gemma-4-26b-a4b-qat
```

`MODEL_HEAVY=deepseek-v4-flash` remains the ds4 heavy backend; ds4 is not replaced by LM Studio.

## Gate G10: Fusion Deliberation Router

G10 adds an OpenRouter-style multi-model deliberation router. When the caller
sends a request with `model=conclava-fusion` (OpenAI Chat / Responses) or
`model=claude-conclava-fusion` (Anthropic Messages), the gateway:

1. Extracts the optional fusion override from the request body (two shapes supported).
2. Resolves a preset (`quality` / `budget` / `coding` / `heavy`) or honors a custom panel.
3. Runs each analysis model **serially** (load → chat → unload → next) via
   LM Studio OpenAI-compatible API.
4. Runs a judge model with a synthesis prompt asking for a 5-section markdown answer.
5. Returns a `FusionAction` whose `text` is the Final Answer section (or raw
   judge text if format was not followed — fallback path).

### Presets

| Preset | analysis_models | judge_model | Peak RAM (serial) |
|---|---|---|---|
| `quality` | qwen3-coder-next (65GB), qwen3.6-35b-a3b (38GB), deepseek-r1-distill-qwen-32b (66GB) | qwen3.6-35b-a3b | ~66GB |
| `budget` | gemma-4-26b-a4b-qat (16GB), qwen3.6-35b-a3b (38GB) | qwen3.6-35b-a3b | ~38GB |
| `coding` | qwen3-coder-next (65GB), qwen3.6-35b-a3b (38GB), deepseek-r1-distill-qwen-32b (66GB) | qwen3-coder-next | ~66GB |
| `heavy` | qwen3-coder-next (65GB), deepseek-r1-distill-qwen-32b (66GB) | ds4 `deepseek-v4-flash` | ~66GB + ds4 |

`FUSION_DEFAULT_PRESET` env var controls the default when caller doesn't
specify. Default is `quality`.

### Request body shapes

Two compatible shapes (resolution order: plugins wins over top-level):

```jsonc
// Shape A — OpenRouter-style plugins
{
  "model": "conclava-fusion",
  "messages": [{"role": "user", "content": "..."}],
  "plugins": [{"id": "fusion", "preset": "quality"}]
}

// Shape B — simplified top-level fusion block
{
  "model": "conclava-fusion",
  "messages": [{"role": "user", "content": "..."}],
  "fusion": {
    "preset": "quality",                    // optional if analysis_models set
    "analysis_models": ["...", "..."],      // optional override
    "judge_model": "..."                    // optional override
  }
}
```

### Curl examples

```bash
# OpenAI Chat + plugins shape
curl -fsS http://127.0.0.1:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "conclava-fusion",
    "messages": [{"role":"user","content":"Compare mergesort vs quicksort for 50k records"}],
    "plugins": [{"id":"fusion","preset":"budget"}]
  }'

# OpenAI Responses + top-level fusion block + custom panel
curl -fsS http://127.0.0.1:8088/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "conclava-fusion",
    "input": "Review this Python function",
    "fusion": {
      "analysis_models": ["qwen/qwen3-coder-next", "qwen/qwen3.6-35b-a3b"],
      "judge_model": "qwen/qwen3.6-35b-a3b"
    }
  }'

# Anthropic Messages
curl -fsS http://127.0.0.1:8088/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-conclava-fusion",
    "messages": [{"role":"user","content":"..."}],
    "max_tokens": 2048,
    "fusion": {"preset":"coding"}
  }'
```

### Output schema (judge synthesis)

The judge model is asked to produce this exact markdown structure:

```markdown
## Final Answer
<1-3 sentence synthesis>

## Consensus
- <point ≥2 panelists agree on>

## Contradictions
- <disagreement between panelists; or "- None">

## Blind Spots
- <area of agreement that should be challenged; or "- None">

## Per-model Notes
### <panelist model id>
<1-2 sentence summary of their analysis>
```

If the judge does not follow the format, the runner falls back to returning
the raw judge text as `text` and sets `confidence=0.5`,
`rationale_summary="fusion_deliberation_fallback_used"`, and
`trace.fusion.structured_had_fallback=True`. **Format compliance is
probabilistic** — reasoning models like qwen3.6 may emit valid answers without
strict markdown section headers. The fallback path is by design.

### Memory invariant

Each panel call is followed by `OllamaClient.unload_models([model_id])`, which
in LM Studio backend issues `lms unload --all`. This guarantees that at most
one model is resident at any time during a deliberation, keeping peak RAM
within the M5 Max 128 GB budget. The judge model is also unloaded after its
call for a clean exit state.

### Error path

Unknown preset name → `FusionAction(type="final_answer", text="fusion-agent
preset error: ...", confidence=0.0, rationale_summary="fusion_preset_error")`.
No model is invoked. HTTP response is still 200 (by design — caller always
gets parseable JSON).

### G10 Gate Acceptance (recorded)

```text
pytest tests/ -q                  → 211 passed, 1 warning
test_fusion_bad_preset.sh         → PASS (descriptive error, no model invoked)
test_fusion_budget.sh             → PASS (raw judge text returned via fallback)
gateway health after restart      → {"status":"ok","version":"1.5.0"}
post-flight ~/.lmstudio/bin/lms ps → "No models are currently loaded"
post-flight curl :11434/api/ps     → {"models":[]}
ds4 still up                       → deepseek-v4-flash + deepseek-v4-pro reachable
```

**Important — reasoning-model max_tokens note**: qwen3.6-35b-a3b is a
thinking/reasoning model that splits output into `content` and
`reasoning_content`. The runner reads `content`. For complex synthesis
prompts, qwen3.6 can consume the entire `max_tokens` budget on reasoning
(`reasoning_tokens == completion_tokens`, `finish_reason == "length"`,
`content == ""`). To get visible content, callers must pass
`max_tokens >= 4000` in the request body. The E2E scripts in
`scripts/test_fusion_*.sh` already pass `max_tokens: 4000` for this
reason. If you see `[fusion produced no output]` in a response, raise the
caller's `max_tokens`.

The G10 E2E test scripts intentionally accept BOTH outcomes:
- Structured (all 5 markdown sections present) — preferred
- Fallback (raw judge text returned, `had_fallback=True`) — acceptable

This matches the runner design where format compliance is probabilistic
against real reasoning models.

## Gate G11: MLX Optimizations

G11 builds on G09 (LM Studio/MLX routing) and G10 (fusion deliberation) to
extract three remaining MLX wins:

### G11-1: Pre-warm launchd jobs

Two new launchd jobs preload panel models before peak usage:

```text
io.github.henrylinyy.conclava.warmup.quality  Mon-Fri 08:00 local
io.github.henrylinyy.conclava.warmup.budget   Mon-Fri 08:05 local
```

Install (idempotent):

```bash
bash scripts/install_warmup_launchd.sh
```

On-demand trigger:

```bash
bash scripts/warmup_now.sh quality
launchctl start io.github.henrylinyy.conclava.warmup.quality
```

Plists live in `Library/LaunchAgents/` (repo) and are symlinked to
`~/Library/LaunchAgents/` by the installer. Logs:
`~/Library/Logs/conclava-warmup-{quality,budget}.{out,err}.log`.

### G11-2: MLX formatter preference

When `CONCLAVA_PREFER_MLX_FORMATTER=true` (default), the `fast-agent`
profile **auto-routes SHORT text-only requests** through `formatter-mlx`
(gemma via MLX, ~16 GB) instead of `fast-agent` (qwen3.6, 38 GB). This saves
the ~30s model-load time of qwen3.6 for trivial text work.

Conditions (ALL must hold):

1. `CONCLAVA_PREFER_MLX_FORMATTER=true`
2. `task.tools == []` (no tool calls)
3. `len(task.text.strip()) < CONCLAVA_MLX_FORMATTER_MAX_CHARS` (default 1000)

Otherwise the standard `fast-agent` path is used. Set
`CONCLAVA_PREFER_MLX_FORMATTER=false` to disable globally.

### G11-3: Streaming fusion deliberation

When `stream=true` is sent to `/v1/chat/completions` with `model =
conclava-fusion` (or `claude-conclava-fusion`), the gateway emits
**OpenAI-compatible SSE events** in real time:

```text
data: {"choices":[{"delta":{"role":"assistant"}}]}                 ← OpenAI standard (start)

data: : fusion preset resolved: budget                            ← SSE comment (caller can ignore)
data: : fusion panel_start: gemma-4-26b-a4b-qat                  ← SSE comment
data: : fusion panel_done: gemma ... (11s, ## Analysis ...)       ← SSE comment
data: : fusion panel_start: qwen3.6-35b-a3b
data: : fusion panel_done: qwen3.6 ... (25s, ## Analysis ...)
data: : fusion judge_start: qwen3.6, ollama

data: {"choices":[{"delta":{"content":"\n\n"}}]}                  ← JUDGE TOKENS (real-time)
data: {"choices":[{"delta":{"content":"##"}}]}
data: {"choices":[{"delta":{"content":" Final"}}]}
data: {"choices":[{"delta":{"content":" Answer"}}]}
... (more tokens) ...

data: {"choices":[{"delta":{},"finish_reason":"stop"}}]}           ← end
data: [DONE]
```

- **Panel / judge lifecycle events**: SSE comments (lines starting with `:`),
  which OpenAI clients ignore by spec. Useful for debug logging.
- **Judge tokens**: real OpenAI `chat.completion.chunk` deltas — each token
  of the judge's response arrives as it generates. This is the **MLX
  streaming path** for fusion deliberation.
- **Final**: standard `finish_reason: "stop"` chunk + `[DONE]`.

The streaming runner calls `OllamaClient.chat_completion_stream()` (sync
generator over httpx SSE) for the judge phase, with `asyncio.run_in_executor`
to keep the event loop free. Panel phase is still sync (single chat per model)
since each model is unloaded before the next starts.

Implementation files:
- `conclava/streaming_events.py`: `FusionStreamEvent` dataclass + 7 event types
- `conclava/models.py`: `OllamaClient.chat_completion_stream()` SSE iterator
- `conclava/fusion_deliberation.py`: `run_fusion_agent_streaming()` async generator
- `conclava/server.py`: `_stream_chat_response` now branches on
  `task.profile == "fusion-agent"` to route to streaming runner

Tests: 5 streaming runner tests + 7 event tests + 5 client tests + existing
237 tests = **238 passing**.

## Gate G12: Streaming Fusion + MLX Operational Polish

G12 adds MLX-friendly optimizations and operational polish on top of
G10 fusion deliberation + G11 MLX formatter preference.

### G12-1: Panel token-by-token streaming

`run_fusion_agent_streaming` now emits `panel_token` events for each
panel model's analysis (in addition to the existing `judge_token` for
the judge). Event ordering per panel: `panel_start → panel_token*N →
panel_done`.

Caller sees the deliberation evolve in real time:

```text
: fusion panel_start: gemma-4-26b-a4b-qat
: fusion panel_token: gemma ... '## Analysis'
: fusion panel_token: gemma ... '\nFor 50k records...'
: fusion panel_done: gemma ... (11s)
: fusion panel_start: qwen3.6
: fusion panel_token: qwen3.6 ... '## Analysis'
...
```

Backwards compatible: if `panel_client` doesn't have `chat_completion_stream`,
runner falls back to `chat_completion` (no panel_token events emitted).

### G12-2: Anthropic Messages streaming fusion

`/v1/messages` with `model=claude-conclava-fusion` + `stream=true` now
emits Anthropic-format SSE:

```text
event: message_start
data: {"type":"message_start", "message":{...}}

event: content_block_start
data: {"type":"content_block_start", "index":0, ...}

event: content_block_delta
data: {"type":"content_block_delta", "index":0, "delta":{"type":"text_delta","text":"..."}}

... (more deltas)

event: message_delta
data: {"type":"message_delta", "delta":{"stop_reason":"end_turn",...}}

event: message_stop
data: {"type":"message_stop"}
```

This completes G11-3 streaming parity across all 3 protocols.

### G12-3: Last-model-resident cache

By default (`keep_last_panel_resident=True`), the runner does NOT unload
the last panel model. The judge model is also kept resident if ollama-based.
LM Studio TTL=1h handles eventual eviction.

Effect: back-to-back fusion requests save ~30s model-load on the 2nd
through Nth request (judge or last panel stays warm).

Quality preset unloads 2 of 3 panel models (last kept). Budget preset
unloads 1 of 2 (last panel + judge are same model — qwen3.6).

### G12-4: `GET /v1/fusion/presets` endpoint

New endpoint exposes fusion preset metadata + runtime state:

```bash
$ curl http://127.0.0.1:8088/v1/fusion/presets
{
  "presets": {
    "quality": {"panel": ["qwen-coder", "qwen3.6", "deepseek-r1"],
                "judge": "qwen3.6", "judge_backend": "ollama", ...},
    "budget":  {"panel": ["gemma", "qwen3.6"], ...},
    "coding":  {...},
    "heavy":   {...}
  },
  "loaded_now": ["google/gemma-4-26b-a4b-qat"],
  "last_used_model": "qwen/qwen3.6-35b-a3b",
  "ds4_reachable": true,
  "default_preset": "quality"
}
```

Also a lightweight `/v1/fusion/presets/loaded` endpoint for polling (no ds4
probe, no preset listing).

### G12-5: Judge fallback chain

When the primary judge model fails (chat_completion raises), the runner
retries with each fallback model in order. Configured via:

```
fusion_judge_fallback_chain: str = "qwen3.6,gemma,r1"  # comma-separated
```

Default chain: qwen3.6 → gemma → r1. Each is tried in turn until one
returns non-empty text. Only after all fail does runner return an error.

### Micro-ops

- **A**: warmup plists set `RunAtLoad=true` — models preload on launchd
  agent load (e.g., after system boot).
- **B**: `CONCLAVA_WARMUP_ON_BOOT=false` env opt-out in warmup scripts.
- **C**: streaming `final` chunk now emits `usage` token counts (OpenAI spec).
- **D**: `FusionCore.last_used_model` instance attribute + `action.trace["last_used_model"]`.
- **E**: `/health` endpoint surfaces `loaded_models` (from `lms ps`) +
  `last_used_model`. Useful for ops monitoring.

### Files changed (G12)

- `conclava/streaming_events.py` — added `FUSION_STREAM_EVENT_PANEL_TOKEN`
- `conclava/fusion_deliberation.py` — panel streaming + judge fallback chain + keep_last_resident threading
- `conclava/fusion_core.py` — `_annotate_trace` helper
- `conclava/config.py` — `keep_last_panel_resident`, `fusion_judge_fallback_chain`
- `conclava/server.py` — Anthropic streaming branch, `/v1/fusion/presets`, `/health` enrichment, usage chunk
- `Library/LaunchAgents/*.plist` — `RunAtLoad=true`
- `scripts/warmup_fusion_*.sh` — `CONCLAVA_WARMUP_ON_BOOT` check
- `.env.example` — `CONCLAVA_WARMUP_ON_BOOT=true`

### Tests

`pytest tests/ -q` → **248 passed** (was 238, +10 from G12 new tests).

New test files:
- `tests/test_fusion_presets_endpoint.py` (3 tests)
- `tests/test_judge_fallback_chain.py` (4 tests)
- `tests/test_fusion_panel_streaming.py` (3 tests)

## Gate G14: Web UI + Persistent Context + CI

G14 ships the user-facing polish: a web dashboard, persistent
conversations, and CI for regression catching.

### G14-1: Web UI dashboard (`/dashboard`)

Single-page HTML+JS app served by the gateway at `GET /dashboard`.
Features:
- Preset selector (4 built-in + custom)
- Model selector (OpenAI Chat / Anthropic Messages)
- Message input with ⌘+Enter to send
- Live streaming events panel (panel_start, panel_token, panel_done,
  judge_start, judge_token, judge_done, final, error)
- Auto-updating loaded models list (polls `/v1/fusion/presets/loaded` every 5s)
- ds4 reachability indicator
- last_used_model display
- Configurable gateway URL (for multi-gateway setups)
- Real-time response box that streams judge tokens

Uses native `fetch()` + `ReadableStream` (no JS dependencies, no build step).
Works in any modern browser.

Open `http://127.0.0.1:8088/dashboard` to use it.

### G14-2: Persistent cross-request context

File-based conversation store at `~/.conclava/conversations/`.
Each conversation is a JSON file with the schema:
```json
{
  "id": "conv-abc123",
  "created_at": 1781804262.123,
  "updated_at": 1781804362.456,
  "messages": [
    {"role": "user", "content": "...", "preset": "quality"},
    {"role": "assistant", "content": "...", "preset": "quality"}
  ],
  "metadata": {"user": "yourname", "topic": "..."}
}
```

API endpoints:
- `POST   /v1/conversations` — create new (body: `{"metadata": {...}}`)
- `GET    /v1/conversations` — list all non-expired
- `GET    /v1/conversations/{id}` — retrieve specific
- `DELETE /v1/conversations/{id}` — delete (returns `{deleted: bool}`)

TTL: 24 hours (configurable). Expired conversations are filtered on
read; `cleanup_expired()` removes them from disk.

Storage: atomic write via `*.json.tmp` → rename. Thread-safe (multiple
processes can read; writes are atomic).

Helper `build_history_block(conv, max_messages=10)` formats the most
recent N exchanges as a single string for injection into the fusion
synthesis prompt. (Runner integration is the next step — see HANDOFF.)

### G14-3: CI / GitHub Actions

`.github/workflows/ci.yml` runs on push to main / develop / gate/* and
on pull requests.

Test job (Python 3.11, 3.12 matrix on macOS-latest for MLX support):
- Install dependencies (pip cache by requirements.txt)
- Cache LM Studio / Ollama (saves 5+ min per run)
- `pytest tests/ -q --tb=short --maxfail=5`
- Coverage report (`xml` + `term-missing`) — uploads to Codecov (3.12 only)

Lint job (Python 3.12):
- `ruff check conclava conclava_sdk tests`
- `ruff format --check conclava conclava_sdk`

CI tests do NOT require real LM Studio / ds4 — all unit tests are
mock-based. E2E scripts (`scripts/test_fusion_*.sh`) run manually on
local M5 Max.

### Files added/changed (G14)

- `.github/workflows/ci.yml` + `.github/workflows/README.md` — new CI
- `conclava/web/dashboard.html` — new web UI (18KB)
- `conclava/conversation_store.py` — new file-based store
- `conclava/server.py` — added `/dashboard`, 4 conversation endpoints, HTMLResponse import
- `tests/test_conversation_store.py` (12 tests)

### Tests

`pytest tests/ -q` → **279 passed** (was 267, +12 G14 new tests).

## Gate G15: MLX Optimization Enablement

G15 turns on the LM Studio MLX optimizations that the 0.4.16 runtime
already supports. Most of these were left at conservative defaults;
this gate pushes them toward the M5 Max 128 GB sweet spot.

### What was on, what we tuned

LM Studio 0.4.16 runtime ships with:
- ✅ **Flash attention** (default ON since 0.2.0)
- ✅ **MLX 8-bit / NVFP4 quantization** (the qwen3.6 MLX-8bit variant is what we use)
- ✅ **Continuous batching** (default `parallel=4` per the loaded model)

G15 explicitly enables / bumps:
- ✅ `defaultContextLength`: **8192 → 32768** (4x more room for long fusion prompts + history)
- ✅ `configPresetInclusiveness.speculativeDecoding`: **false → true** (no-op until a draft model is downloaded)
- ✅ `lms load --parallel 2 --gpu max` in warmup scripts (was implicit default; now explicit + M5-tuned)
- ✅ `lms load --ttl 3600` in warmup (auto-unload after 1h idle)

### New endpoint: `GET /v1/system/optimizations`

```bash
$ curl http://127.0.0.1:8088/v1/system/optimizations
{
  "lmstudio_version": "CLI commit: efce996",
  "active_runtime": "llama.cpp-mac-arm64-apple-metal-advsimd",
  "context_length": 32768,
  "speculative_decoding": true,
  "current_loaded_models": [...],
  "draft_model_configured": false,
  "recommended_settings": {
    "context_length": 32768,
    "parallel": 2,
    "gpu_mode": "max",
    "note": "M5 Max 128GB tuned"
  }
}
```

### What you actually see

Before G15 (LM Studio 0.4.16 defaults):
```
CONTEXT    PARALLEL    SIZE
8192       4           37.75 GB
```

After G15 (settings.json + warmup tuned):
```
CONTEXT    PARALLEL    SIZE
32768      2           35.16 GB   ← less RAM, 4x longer context
```

Longer context lets fusion deliberation handle:
- Long source documents (entire code files as fusion input)
- Multi-turn conversations with history (G14-2)
- Long system prompts (richer preset system prompts are now feasible)

### About speculative decoding

The flag is now set to true in `settings.json`, but **no effect** until
you download a small draft model. To enable:

```bash
# Download a small qwen3 draft (~1-2 GB) for speculative decoding with qwen3.6
~/.lmstudio/bin/lms get qwen2.5-1.5b-instruct

# Then in LM Studio chat UI: model config → enable speculative decoding
# The draft model pairs with the larger one and gives 2-3x throughput
```

For M5 Max 128 GB you have headroom for a 1-3 GB draft model on top of
your 252 GB model collection. The draft only needs to be the same family
(small qwen for big qwen, etc.).

### Paged attention + continuous batching + chunked prefill

These are 0.4.16 runtime features. Paged attention is automatic.
Continuous batching is the `parallel=N` setting (we use 2). Chunked
prefill isn't yet exposed via `lms load` flags — needs a future
LM Studio version (0.5.x?) to enable via CLI.

### Files added/changed (G15)

- `conclava/mlx_optimizations.py` — new module:
  - `apply_recommended_settings()` — bumps context, enables spec decoding
  - `get_current_optimizations()` — for /v1/system/optimizations endpoint
  - Idempotent, with backup support
- `conclava/server.py` — added `/v1/system/optimizations` endpoint
- `scripts/warmup_fusion_quality.sh` + `warmup_fusion_budget.sh` — G15:
  - Added `FUSION_WARMUP_CONTEXT_LENGTH` (default 32768)
  - Added `FUSION_WARMUP_PARALLEL` (default 2)
  - Added `FUSION_WARMUP_GPU_MODE` (default max)
  - Added `FUSION_WARMUP_TTL` (default 3600s)
  - Auto-apply `apply_recommended_settings()` at warmup start
- `tests/test_mlx_optimizations.py` (8 tests)
- `~/.lmstudio/settings.json` — bumped (auto-applied)

### Tests

G15 snapshot: `pytest tests/ -q` → **287 passed** (was 279, +8 G15 new tests).

Apply anytime with:
```bash
./.venv/bin/python -m conclava.mlx_optimizations
```

## G15.1: Speculative Decoding — Setup Status

Attempted to fully enable speculative decoding in LM Studio 0.4.16.
Result: **draft model is downloaded and ready, but the draft-target
pairing must be done via the LM Studio GUI** (no CLI/API support in
0.4.16 for this specific configuration step).

### What was set up

```bash
# 1. Downloaded qwen3-1.7b as draft model (~1.84 GB MLX)
~/.lmstudio/bin/lms get --mlx -y "qwen3-1.7b"

# 2. Both models loaded simultaneously
~/.lmstudio/bin/lms load "qwen/qwen3.6-27b" --context-length 8192 --gpu max
~/.lmstudio/bin/lms load "qwen/qwen3-1.7b" --context-length 8192 --gpu max

# 3. speculativeDecoding flag in settings.json (already set in G15)
configPresetInclusiveness.speculativeDecoding = true
```

### What is NOT supported via CLI

LM Studio 0.4.16 exposes speculative decoding **only via the chat UI**:
- Settings icon → Adjust Parameters → Speculative Decoding → Draft Model dropdown
- No `--draft-model` flag in `lms load`
- No `draft_model` field in `/v1/chat/completions` request body
- No draft-model field in any persistent config file
- CLI commit `efce996` doesn't expose this

### What the user needs to do (3 minutes)

1. **Open LM Studio** (already running, on this Mac)
2. Click **'qwen/qwen3.6-27b'** in the chat panel (the loaded target model)
3. Click **⚙️ Settings icon** (top right) → **Adjust Parameters**
4. Find **Speculative Decoding** section
5. In the **Draft Model** dropdown, select **'qwen/qwen3-1.7b'**
6. **Save as Preset** (e.g., name it `qwen3.6-with-1.7b-draft`)
7. Re-load qwen3.6-27b — it now uses the draft
8. Re-run the benchmark script to measure speedup:

```bash
./.venv/bin/python scripts/benchmark_speculative.py
```

### Expected speedup

Theoretical: 2-3x for typical chat. qwen3-1.7b drafts likely 5-10 tokens
at a time; qwen3-6-27b verifies all in one forward pass. For long
generations, the speedup is bigger.

### Why CLI doesn't expose this

The config-presets system in LM Studio is app-internal. The CLI only
exposes model lifecycle (load/unload/ls/ps). Draft model assignment
is bound to a chat preset, which is GUI-managed.

If a future LM Studio CLI version adds `--draft-model` to `lms load`,
this script + HANDOFF section will work automatically.

### Files added (G15.1)

- `scripts/benchmark_speculative.py` — measures tokens/sec, prints
  UI pairing steps, saves baseline to `~/.conclava/spec_decode_baseline.json`

### Baseline measured (before UI pairing)

- qwen3.6-27b @ 8K context, 100 tokens
- **6.16s wall time, 16.08 tokens/sec**
- Run again after UI pairing to compare.

### G15.2: Speculative Decoding — Final Status (after family investigation)

Attempted to find a compatible draft model for `qwen/qwen3.6-27b:2`
(the currently active target). Investigated the family matching
requirements:

| Model | Family | Compatible draft? |
|---|---|---|
| `qwen/qwen3.6-27b` (27B) | `qwen3_5` | ❌ No qwen3_5 small draft in LM Studio |
| `qwen/qwen3.6-35b-a3b` (35B) | `qwen3_5_moe` | ❌ Same — no draft available |
| `qwen/qwen3-coder-next` (80B) | `qwen3_next` | ❌ qwen3-0.6b is `qwen3` (different) |
| `qwen/qwen3-1.7b` (1.7B) | `qwen3` | ✓ if target were `qwen3` family |
| `qwen/qwen3-0.6b` (0.6B) | `qwen3` | ✓ if target were `qwen3` family |
| `qwen/qwen3-4b` (4B) | `qwen3` | ✓ if target were `qwen3` family |
| `deepseek-r1-distill-qwen-32b` | Qwen2 | ❌ No Qwen2 small draft |

**Conclusion**: LM Studio 0.4.16 strictly requires draft and target to share
the same architecture family. Our model collection has multiple
different qwen families (qwen3, qwen3_5, qwen3_next) but no qwen3_5 or
qwen3_next small variants exist in the LM Studio catalog. As a result,
**none of the large models in the current collection can be paired with
a draft for speculative decoding**.

**Workarounds** (none fully resolve this):

1. **Wait for LM Studio 0.5.x** — may relax family matching or add
   qwen3.5 small variants to the catalog
2. **Add a qwen3.5 small model manually from HuggingFace**:
   ```bash
   # qwen3.5 small variants exist on HF but not in LM Studio catalog
   ~/.lmstudio/bin/lms get https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
   ```
3. **Switch to a different target architecture** — but all fusion models
   are qwen3_5 / qwen3_next / Qwen2; none are qwen3 (the family we have
   drafts for)
4. **Run speculative decoding via llama.cpp CLI directly** (bypass
   LM Studio) — out of scope for this project

**Pragmatic decision**: skip speculative decoding for now. The other
G15 optimizations (32K context, parallel=2, auto-apply settings) are
in place and deliver measurable wins. Re-evaluate when:
- LM Studio adds qwen3.5 small draft models
- A new LM Studio version relaxes family matching
- HuggingFace releases a qwen3.5 small variant that can be manually added

### Files added (G15.2)

- `scripts/benchmark_speculative.py` — still useful for re-measurement
  if/when draft model becomes available
- Updated HANDOFF.md G15.1 section with honest assessment of what
  worked and what didn't
- Verified all qwen3 small drafts (0.6b, 1.7b, 4b) are present and loaded
  but unusable due to family mismatch with main models

## Gate G13: SDK + Streaming Parity + Retry

G13 closes the remaining gaps from G11-3 / G12 and adds a proper Python
client library.

### G13-1: Python SDK (`conclava_sdk/`)

New first-class Python client package:

```python
from conclava_sdk import ConclavaClient, FusionPreset

client = ConclavaClient("http://127.0.0.1:8088")

# Introspection
presets = client.list_presets()
state = client.loaded_models()
print(client.health())

# Non-streaming fusion
result = client.fusion_chat(
    messages=[{"role": "user", "content": "..."}],
    preset=FusionPreset.QUALITY,
)
print(result.text)

# Streaming (sync iterator)
for event in client.fusion_chat_stream(
    messages=[{"role": "user", "content": "..."}],
    preset=FusionPreset.BUDGET,
):
    if event.event == "judge_token":
        print(event.judge.delta, end="", flush=True)

# Async variant
result = await client.afusion_chat(messages=[...], preset=FusionPreset.CODING)
```

Public surface:
- `ConclavaClient(base_url, timeout, max_tokens)`
- `FusionPreset` enum: `QUALITY | BUDGET | CODING | HEAVY | CUSTOM`
- `FusionEvent`, `PanelEvent`, `JudgeEvent`, `FinalEvent`, `ErrorEvent` dataclasses
- `FusionResult` dataclass with text, structured, trace, timing

E2E verified against real gateway: 272 streaming events received
in budget preset run; `list_presets()` returns all 4 presets with
correct metadata; ds4_reachable=True.

### G13-2: OpenAI Responses streaming fusion

`_stream_openai_response` now branches on `task.profile == "fusion-agent"`.
Maps FusionStreamEvent → OpenAI Responses SSE format:

```text
event: response.created
data: {"type":"response.created", "response":{...}}

event: response.in_progress
data: {"type":"response.in_progress", ...}

event: response.output_text.delta
data: {"type":"response.output_text.delta", "delta":"..."}

... (more deltas)

event: response.completed
data: {"type":"response.completed", "response":{..., "usage":{...}}}
```

This completes streaming parity across all 3 protocols:
- OpenAI Chat Completions (G11-3)
- OpenAI Responses (G13-2)
- Anthropic Messages (G12-2)

### G13-3: Retry with exponential backoff

New helper `conclava.fusion_retry.chat_with_retry` wraps
chat_completion calls with exponential backoff. Only retries on
**transient** errors (`TimeoutError`, `ConnectionError`, httpx network
errors). Does NOT retry on 4xx, `ValueError`, `KeyError`, etc.

Config:
- `FusionConfig.fusion_max_retries` (default `0` = no retry; `2` = up to 2 retries = 3 total attempts)
- `FusionConfig.fusion_retry_base_delay` (default `1.0s`; doubles each retry: 1s, 2s, 4s)

Wired into:
- Judge `chat_completion` (helps with LM Studio first-call cold load)
- Panel fallback path (non-streaming chat, when streaming unavailable)

Enable with: `FUSION_MAX_RETRIES=2 FUSION_RETRY_BASE_DELAY=1.0` in `.env`.

### Files added/changed (G13)

- `conclava_sdk/__init__.py` + `client.py` + `events.py` + `types.py` — new SDK
- `conclava/fusion_retry.py` — new retry helper
- `conclava/config.py` — added `fusion_max_retries`, `fusion_retry_base_delay`
- `conclava/fusion_deliberation.py` — judge + panel non-streaming wrapped with retry
- `conclava/server.py` — `_stream_openai_response` fusion-agent branch
- `tests/test_conclava_sdk.py` (10 tests)
- `tests/test_fusion_retry.py` (9 tests)

### Tests

`pytest tests/ -q` → **267 passed** (was 248, +19 G13 new tests).

```bash
cd conclava
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Review `.env` before starting services. Defaults bind the gateway to `127.0.0.1:8088` and the LM Studio OpenAI-compatible backend to `127.0.0.1:1234/v1`.

## Required Local Services

LM Studio local model server:

```bash
~/.lmstudio/bin/lms server status
~/.lmstudio/bin/lms server start   # if needed
bash scripts/pull_models.sh        # verifies local LM Studio ids
bash scripts/pull_mlx_models.sh
bash scripts/pull_vision_models.sh
bash scripts/test_ollama.sh        # legacy script name; now probes LM Studio /v1/chat/completions
bash scripts/test_ollama_tools.sh
bash scripts/test_vision_fast.sh
bash scripts/test_vision_pro.sh
bash scripts/test_agentic_pro.sh
bash scripts/test_agentic_mlx.sh
bash scripts/test_formatter_mlx.sh
```

ds4:

```bash
bash scripts/setup_ds4.sh
bash scripts/start_ds4.sh
bash scripts/test_ds4.sh
```

Gateway:

```bash
bash scripts/start_server.sh
```

Persistent local launchd job installed on this machine:

```bash
launchctl print gui/$(id -u)/io.github.henrylinyy.conclava.gateway
launchctl kickstart -k gui/$(id -u)/io.github.henrylinyy.conclava.gateway
launchctl bootout gui/$(id -u)/io.github.henrylinyy.conclava.gateway
```

Plist: `~/Library/LaunchAgents/io.github.henrylinyy.conclava.gateway.plist`. Logs: `~/Library/Logs/conclava-gateway.out.log` and `~/Library/Logs/conclava-gateway.err.log`.

Ollama may still be installed for other workflows, but Conclava G09 routes local non-ds4 profiles through LM Studio by default. Keep Ollama resident models unloaded unless explicitly testing Ollama.

Previous temporary launchd job reference (remove if found):

```bash
launchctl print gui/$(id -u)/conclava-gateway-m5-g06g
launchctl remove conclava-gateway-m5-g06g
```

## Verification

Unit and endpoint tests mock LM Studio/Ollama-compatible clients and ds4:

```bash
./.venv/bin/python -m pytest tests/ -q
```

Runtime checks:

```bash
curl http://127.0.0.1:8088/health
curl http://127.0.0.1:8088/v1/models
curl http://127.0.0.1:1234/v1/models
~/.lmstudio/bin/lms ps
curl http://127.0.0.1:11434/api/ps   # should not show qwen3-coder unless explicitly testing Ollama
```

Expected route surface, excluding FastAPI docs/openapi helper routes:

```text
routes=7 GET=3 POST=4
```

Manual E2E acceptance and model/profile details are documented in `README.md`.

## Package Contents

The handoff archive includes source code, tests, scripts, README, this handoff note, `.env.example`, `requirements.txt`, and `pyproject.toml`.

The archive intentionally excludes:

```text
.venv
.env
__pycache__
.pytest_cache
.DS_Store
LM Studio model weights
Ollama model blobs
ds4 build/runtime directories
/tmp logs
```

Model weights are not packaged. Recreate/download local weights through LM Studio and verify with the helper scripts above.

## Known Limits

- Streaming is keepalive plus final/event streaming, not token-by-token model streaming.
- Only one tool call per round is supported.
- Parallel requests are intentionally rejected by the global request lock.
- The server is stateless and does not persist `previous_response_id`.
- VisionEvidence keeps vision extraction auditable; vision models do not directly execute tools.
- `vision-heavy` remains two-stage: vision extraction first, unload resident local model backend, then ds4 heavy reasoning.
- **LM Studio routing (gate G09)**: local non-ds4 profiles use `LOCAL_MODEL_BACKEND=lmstudio` and `OLLAMA_BASE_URL=http://127.0.0.1:1234/v1` (historical env name kept for compatibility). `OllamaClient` is now a compatibility client for LM Studio/OpenAI-compatible chat as well as Ollama.
- **LM Studio profiles**: `conclava-agentic-mlx` maps to `MODEL_AGENTIC_MLX=qwen/qwen3.6-35b-a3b`; `conclava-formatter-mlx` maps to `MODEL_FORMATTER_MLX=google/gemma-4-26b-a4b-qat`.
- **Context loading**: LM Studio auto-load may default to 8K context. For large-context work, pre-load the intended model with `~/.lmstudio/bin/lms load --context-length 131072 --gpu max <model-id>` before sending long prompts.
- **Resource guard**: LM Studio model sizes are larger than the previous fast defaults (`qwen/qwen3-coder-next` ≈ 65GB, `deepseek-r1-distill-qwen-32b` ≈ 66GB). Keep serial execution; do not keep qwen-coder-next + deepseek + ds4 resident together.
- ds4 remains a beta heavy backend and must keep full-agent fallback available.
- **G10 Fusion deliberation router**: panel models run serially (not parallel) because M5 Max 128 GB cannot fit two 65 GB models concurrently. Streaming token-by-token is not supported for the panel phase; the entire panel must complete before the judge call. Judge format compliance is probabilistic — if the judge model does not emit the 5-section markdown, the runner falls back to raw text (logged as `fusion_deliberation_fallback_used` with `confidence=0.5`). Structured output is the goal, not a guarantee. The `heavy` preset requires ds4 to be up; running it without ds4 returns an error in the judge step. `conclava-fusion` and `claude-conclava-fusion` are the only model ids that trigger fusion routing.
