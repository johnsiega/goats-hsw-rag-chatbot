# README Showcase Design

## Intent

Present the Goats HSW Rights Chatbot as a polished academic and portfolio project for professors, recruiters, and GitHub visitors, using the supplied Kumpas README as the structural reference.

## Goals

- Lead with a centered project identity, concise tagline, technology badges, live link, and the existing desktop screenshot.
- Explain the problem, user flow, RAG pipeline, local setup, Cloud Run deployment, privacy, limitations, technology, team, and verification.
- State the Groq-to-OpenRouter fallback and third-party processing accurately.
- Keep detailed deployment history in `HOSTING_NOTES.md` and test evidence in `verification/report.md`.

## Non-goals

- No application, prompt, retrieval, UI, API, deployment, or secret changes.
- No invented logo, team-member names, performance claims, or legal guarantees.
- No duplication of the full hosting runbook.

## Approach

Use the Kumpas README's full showcase structure, adapted to this project. The existing `verification/ui_v4_desktop.png` becomes the hero image because the repository has no Goats logo. A compact README was rejected because it would not provide the requested portfolio-style presentation; copying the Kumpas text directly was rejected because its product flow and technology are unrelated.

## Validation

Check all relative links and image paths, confirm commands match the repository, scan the rendered source for stale Hugging Face wording, and run the mock fallback test to ensure documentation work did not disturb the verified tree.
