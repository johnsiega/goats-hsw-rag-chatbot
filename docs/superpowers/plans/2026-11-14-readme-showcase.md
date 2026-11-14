# README Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the compact project README with a polished, accurate GitHub showcase modeled on the supplied Kumpas README.

**Architecture:** This is a documentation-only change. `README.md` will provide the public project narrative and link to existing evidence rather than duplicating operational detail.

**Tech Stack:** Markdown, HTML alignment tags, Shields.io badges, Gradio, Python, Google Cloud Run, Groq, OpenRouter

**Spec:** `docs/superpowers/specs/2026-11-14-readme-showcase-design.md`

## Global Constraints

- Do not modify application behavior, prompt, retrieval, UI, API, deployment, secrets, or limits.
- Use `verification/ui_v4_desktop.png` as the hero image.
- Do not invent team-member names, claims, or test results.
- Disclose that fallback requests may be processed by OpenRouter and routed to Groq.

## Review Focus

- GitHub image rendering: the hero path must resolve with exact filename casing.
- Live app access: the public Cloud Run URL must remain exact.
- Setup accuracy: commands and required environment variable names must match the repository.
- Privacy wording: distinguish app logging from third-party processing.
- Scope accuracy: clearly label the project as informational and not legal advice.

---

### Task 1: Rewrite and verify the project README

**Files:**
- Modify: `README.md`
- Reference: `HOSTING_NOTES.md`
- Reference: `verification/report.md`
- Reference: `verification/ui_v4_desktop.png`

**Interfaces:**
- Consumes: Existing deployment URL, stack versions, run commands, privacy notes, and verification results.
- Produces: A self-contained GitHub landing page with links to deeper evidence.

- [ ] **Step 1: Replace the compact README**

Add the centered header, tagline, badges, hero image, overview, purpose, usage, RAG explanation, local run instructions, Cloud Run notes, privacy and limitations, stack, team, and verification sections described in the spec.

- [ ] **Step 2: Validate repository-relative references**

Run a local script that extracts relative Markdown links and image sources from `README.md`; expect every referenced path to exist.

- [ ] **Step 3: Check documentation integrity**

Run `git diff --check`; expect no whitespace errors. Search the README for stale Hugging Face deployment instructions; expect none.

- [ ] **Step 4: Re-run the mock fallback verification**

Run `python verification/test_fallback.py`; expect `test_fallback: ALL PASS` and prompt SHA-256 `e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a`.

- [ ] **Step 5: Commit and push**

Commit the README, design, and plan files with a documentation-focused message and push `main` to `origin`.
