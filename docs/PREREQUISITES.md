# Prerequisites & Manual Downloads

This file lists **everything you must install manually** on a target machine, with
exact versions. Everything else is handled by `requirements*.txt` (Python) and
`package.json` (Node) so the rest installs in one step. Nothing here requires
administrator rights — all tools install per-user.

> This project was scaffolded on a machine with **Python 3.14** and **Node 25**,
> where the ML wheels don't reliably build. The versions below are the *supported,
> reproducible* runtime the project is pinned to.

---

## 1. Python 3.12 (required)

Why 3.12 and not 3.13/3.14? `numpy`, `scikit-learn`, and (optionally)
`torch`/`sentence-transformers` publish prebuilt wheels for 3.12 but often lag on
brand-new Python releases. Pinning 3.12 guarantees `pip install` succeeds without a
compiler.

- Download: https://www.python.org/downloads/release/python-3127/
  (Windows "installer (64-bit)"; choose **"Install for me only"** — no admin).
- Verify: `py -3.12 --version` → `Python 3.12.x`

## 2. Node.js 20 LTS (required only for the dashboard)

Any Node 18+ works; **20 LTS** is recommended for stability with Vite 6.
- Download: https://nodejs.org/en/download (or use the version already installed).
- Verify: `node --version`

### Windows PowerShell note (important on locked-down machines)
If you see: *"npm.ps1 cannot be loaded because running scripts is disabled"*,
your execution policy blocks the `npm` PowerShell shim. **Do not change system
policy.** Instead either:
- Use the CMD shim directly: `npm.cmd install` / `npm.cmd run dev`, **or**
- Run installs from `cmd.exe` instead of PowerShell, **or**
- Set policy for the current user only (no admin):
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## 3. git (optional)

Not required to run the project; only needed to push to GitHub. It was **not
installed** on the scaffolding machine.
- Download: https://git-scm.com/download/win (per-user install available).

## 4. Optional: MiniLM model weights (~90 MB, one-time)

The semantic layer uses `sentence-transformers/all-MiniLM-L6-v2`. It downloads
automatically on first run **only if** you installed `requirements-ml.txt` and have
internet. **If it can't download, the app automatically falls back to TF-IDF** — no
action needed. To pre-cache it offline, download the model folder from
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 and set
`HF_HOME` / `TRANSFORMERS_CACHE` to its location.

## 5. Optional: Ollama (only if using a local LLM instead of the mock)

- Download: https://ollama.com/download
- Then: `ollama pull llama3.2` and set `GUARDRAIL_LLM_PROVIDER=ollama`.

---

## Version summary

| Component | Version | Required? | Notes |
|-----------|---------|-----------|-------|
| Python | 3.12.x | Yes | Pinned runtime for ML wheels |
| Node.js | 20 LTS (18+) | Dashboard only | Use `npm.cmd` if PowerShell blocks scripts |
| git | latest | Optional | For GitHub only |
| MiniLM weights | all-MiniLM-L6-v2 | Optional | Auto-downloads; TF-IDF fallback otherwise |
| Ollama | latest | Optional | Only for local real LLM |

Python packages are pinned in `backend/requirements.txt` (core, offline-capable),
`backend/requirements-ml.txt` (optional MiniLM/torch), and
`backend/requirements-postgres.txt` (optional Postgres driver), and
`backend/requirements-dev.txt` (tests). Node packages are pinned in
`frontend/package.json`.
