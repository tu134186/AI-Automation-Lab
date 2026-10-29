# AI Automation Lab — Agent Instructions

## Scope and safety
- This repository is an isolated sandbox for testing AI-assisted automation. Never access or modify other repositories without a separate explicit request.
- Do not store secrets, personal data, access tokens, or credentials in commits, logs, or reports.
- Prefer changes on a dedicated feature branch and review before merging to main.
- Never trigger paid cloud builds or deploy to production without explicit authorization.
- Explain what was actually executed versus what remains unverified.

## Workflow
1. Inspect repository files and existing automation before editing.
2. State the intended outcome and acceptance checks.
3. Make focused, reversible changes.
4. Run available local checks; record failures accurately.
5. Report changed files, tests, commit SHA, and remaining risks.
6. Do not claim that a GitHub Actions run or Codex cloud environment succeeded without inspecting its status.

## CLI checks
- Detect tools using `command -v git`, `command -v gh`, `command -v python3`, and `command -v node`.
- If GitHub CLI is installed, use `gh auth status` to inspect authentication without exposing tokens.
- Do not install dependencies or request elevated privileges unless necessary.
