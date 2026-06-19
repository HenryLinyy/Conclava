# Launch kit — Conclava

Three ready-to-post drafts. The README is the landing page; **these are what actually drive traffic to it.** Post order I'd recommend: r/LocalLLaMA first (your core audience, best signal), then Show HN, then the X thread to amplify whatever lands.

> One honest pre-flight check before posting anywhere: the crowd *will* scrutinize your model names (`qwen3.6-35b-a3b`, `gemma-4-26b-a4b-qat`, `deepseek-v4-flash`, `qwen3-coder-next`). Make sure each maps to a model people can actually download, or add a line explaining they're your local aliases — otherwise the top comment becomes "what is qwen3.6" instead of talking about your work.

---

## 1) Show HN

**Title** (80-char limit — keep it tight):

```
Show HN: Conclava – run Claude Code and Codex on your Mac, with a model council
```

**Body:**

> I kept wanting "Claude Code, but fully local" — and got annoyed that one local model is good at chat, another only at code, and reasoning/vision each need their own weights. So I built a gateway that hides all of that behind one endpoint.
>
> Conclava runs on `127.0.0.1:8088` and speaks three agent protocols at once: OpenAI Responses (Codex), Anthropic Messages (Claude Code), and OpenAI Chat (any OpenAI-SDK client). You point the agent CLI you already use at it — base URL swap, zero code changes — and it routes each request to the right specialist model (coder, reasoner, vision, fast formatter).
>
> The part I'm most happy with is "fusion deliberation": call a `*-fusion` model and it convenes a panel of local models, runs them **serially** (load → answer → unload), then a judge synthesizes their answers into Final Answer / Consensus / Contradictions / Blind Spots / Per-model Notes. Because it's serial, a 3-model "council" fits in one 128GB Mac — peak RAM never exceeds the largest single model. It's an OpenRouter-style multi-model panel, but local and memory-bounded.
>
> Built and tuned on an M5 Max (128GB). 287 tests, CI on macOS. Honest limits up front: single workstation, serial execution (no parallel requests), one tool call per turn, and yes it wants a lot of RAM by default.
>
> Repo: https://github.com/HenryLinyy/conclava
> Would love feedback from people running local coding agents — especially on the deliberation output format and where the routing picks the wrong specialist.

---

## 2) r/LocalLLaMA

**Title:**

```
I made Claude Code and Codex run 100% local on a 128GB Mac — with a multi-model "council" that fits in RAM by running serially
```

**Body:**

> Sharing a side project: **Conclava**, a local gateway that makes a fleet of specialized local models behave like one cloud endpoint.
>
> **The problem it solves.** A single local model is narrow — chat-tuned, or code-tuned, and reasoning/vision want dedicated weights. Cloud providers hide that behind one smart endpoint. I wanted the same on my own machine, and I wanted the agent tools I already use (Claude Code, Codex) to just work against it.
>
> **What it does:**
> - One gateway, three protocols at once: `/v1/responses` (Codex), `/v1/messages` (Claude Code), `/v1/chat/completions` (anything OpenAI-compatible). Base-URL swap, no code changes.
> - Task-aware routing to specialists: coder, tool-runner, critic, judge, vision VLM, and a lightweight MLX fast-path for short prompts (skips ~30s of model load).
> - **Fusion deliberation** — the fun part. A panel of models answers, a judge synthesizes into *Final Answer / Consensus / Contradictions / Blind Spots / Per-model Notes*.
>
> **The RAM trick.** The panel runs **serially**: load model → get answer → `unload` → next. So a 3-model council's peak memory never exceeds the largest single model. On a 128GB M5 Max the `quality` preset (coder ~65GB + agentic ~38GB + reasoner ~66GB, judged by the agentic model) peaks at ~66GB instead of ~169GB. You trade latency for the ability to run a "committee" on one box.
>
> **Presets** (panel → judge → peak RAM):
> - `quality`: coder + agentic + reasoner → agentic → ~66GB
> - `budget`: fast + agentic → agentic → ~38GB
> - `coding`: coder + agentic + reasoner → coder → ~66GB
> - `heavy`: coder + reasoner → ds4 heavy backend → ~66GB + ds4
>
> **Stack:** FastAPI gateway + LM Studio (OpenAI-compatible backend) + an optional heavy long-context backend. SSE streaming with per-panel progress events, a single-file live dashboard, a Python SDK, 287 tests, macOS CI.
>
> **Honest limits:** single workstation, serial only (no parallel requests), one tool call per turn, streaming is keepalive+chunk on most paths (the judge path streams tokens), stateless. Default presets assume a lot of unified memory.
>
> Repo + setup for Claude Code / Codex in the README: https://github.com/HenryLinyy/conclava
>
> Happy to answer questions about the routing logic or the deliberation prompt. What would you want the judge to output beyond the five sections?

---

## 3) X / Twitter thread

**1/**
> I made Claude Code *and* Codex run 100% locally on my Mac.
>
> One endpoint. A fleet of specialized models behind it. And a "council" mode where several local models debate and a judge picks the winner — all inside 128GB.
>
> Meet Conclava 🧵

**2/**
> The problem: one local model is good at chat, another only at code, and reasoning/vision each need their own weights.
>
> Cloud hides that behind one smart endpoint. Conclava does the same — on your own machine.

**3/**
> It speaks 3 agent protocols at once on `127.0.0.1:8088`:
> • OpenAI Responses → Codex
> • Anthropic Messages → Claude Code
> • OpenAI Chat → any OpenAI client
>
> Point the agent you already use at it. Base-URL swap, zero code changes.

**4/**
> Each request routes to the right specialist: coder, reasoner, vision, or a lightweight MLX fast-path for short prompts that skips ~30s of model load.
>
> Specialization, not one generalist forced to do everything.

**5/**
> The best part — fusion deliberation 🤝
>
> A panel of models answers, a judge synthesizes into:
> Final Answer / Consensus / Contradictions / Blind Spots / Per-model Notes.
>
> A second and third opinion, baked in.

**6/**
> "But a 3-model council needs 169GB of RAM?"
>
> No. It runs serially: load → answer → unload → next. Peak RAM never exceeds the largest single model.
>
> On a 128GB M5 Max, a 3-model panel peaks at ~66GB. You trade latency for a committee on one box.

**7/**
> Honest about limits: single workstation, serial (no parallel requests), one tool call per turn, wants a lot of RAM.
>
> 287 tests, macOS CI, live dashboard, Python SDK.
>
> Repo 👇 (stars appreciated, feedback more so)
> https://github.com/HenryLinyy/conclava

---

## Posting tips

- **Lead with the demo.** A 20–30s screen recording — Claude Code answering from your local gateway, then a `*-fusion` call streaming panel→judge in the dashboard — will outperform every paragraph here. Pin it to the README top and attach it to the X thread.
- **Be in the comments for the first 3 hours.** On both HN and Reddit, early author responsiveness is the single biggest driver of whether a post climbs.
- **Don't cross-post simultaneously.** Stagger by a day so each community feels native, and so you can fold the first round of feedback into the next post.
- **Title is 90% of it.** If you only A/B test one thing, test the title.
