# Verification report: Goats HSW RAG chatbot (hosted on Google Cloud Run)

## v5 (Groq to OpenRouter fallback), 2026-11-11: deployed

Live: revision `goats-hsw-rag-chatbot-00019-van` (image `v5`) at 100%; rollback `00016-qaz` (v4):
`gcloud run services update-traffic goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --to-revisions goats-hsw-rag-chatbot-00016-qaz=100`

| Check | Result |
|---|---|
| Mock test `verification/test_fallback.py` (no model load) | PASS: OpenRouter body exact (model, messages, temperature 0, max tokens 1500, reasoning low, provider order groq, no fallbacks), primary path unchanged and never calls OpenRouter, rate/daily/connection fall back once, pacer and other errors do not, no key or bad response gives "busy", hook inert unless `FORCE_GROQ_FAIL=1`, prompt SHA-256 `e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a` |
| Live 1: throwaway `00018-xuq`, tag `fbtest`, 0% traffic, `FORCE_GROQ_FAIL=1` | PASS: one question answered with sources; Cloud Logging showed `fallback used` (33 s including cold start) |
| Live 2: final `00019-van`, tag `v5test`, 0% traffic, no hook | PASS: answered with sources, no `fallback` log line (normal Groq path); env has no `FORCE_GROQ_FAIL` |
| Live 3: public URL after switch | PASS: answered in 2.7 s |

Only 3 live questions were used; no evaluation was run. Not tested live: a real Groq rate limit (only the forced failure), and whether OpenRouter's answer text matches Groq's. The prompt hash on the deployed image was not read from the container; the image was built from the same `app.py` (SHA-256 `065aacf7...e2e36`) whose prompt hash the test checks.

**Privacy:** when Groq is limited, the question and retrieved passages may be sent to OpenRouter (third party), pinned to route to Groq. The app itself does not log questions or answers; the only new log line is the fixed text `fallback used`. The throwaway revision and tag `fbtest` were deleted. Secrets: `GROQ_API_KEY:2`, `OPENROUTER_API_KEY:1`; no value was printed.

Hosting target: **Google Cloud Run** (project `goats-hsw-rag-1110`, region `asia-southeast1`).
The plan was a free Hugging Face Space, but Hugging Face answered `402 Payment Required` ("hosting Gradio and Docker Spaces on free cpu-basic requires a PRO subscription"), so nothing was created on Hugging Face and the target was switched to Cloud Run.

Public URL: https://goats-hsw-rag-chatbot-626564095782.asia-southeast1.run.app
(the same service also answers at https://goats-hsw-rag-chatbot-edc7oz3psq-as.a.run.app)

**Final live revision:** `goats-hsw-rag-chatbot-00005-bav`, image `v3`, 100% of traffic (rollback: `00004-9pb`, image `v2`, tag `v2rollback`). Sections 1 to 5 below were first run on image `v2`; the section "Final revision (image v3)" at the end gives the re-run on the final revision.

## Where each check ran, and why

| Check | Where it ran | Why |
|---|---|---|
| 1 Prompt parity | On the PC (no model needed) | Only hashes text |
| 2 Embedding parity | **In the cloud**, through the deployed service | The PC could not load BAAI/bge-m3: Windows had about 1.9 GB of virtual memory free and the model needs about 2.3 GB (access violation / "not enough memory"). The model runs inside the Cloud Run container instead. |
| 3 Retrieval parity | **In the cloud**, through the deployed service | Same reason |
| 4 Answer sanity | Generation in the cloud via `gradio_client`; comparison on the PC | Uses the Groq key stored in Secret Manager |
| 5 UI smoke test | Public URL via `gradio_client` and a real browser at phone width; the key-unset path in a local child process | Cloud Run's key cannot be unset without a redeploy |

Checks 2 and 3 were **not** run locally. To read the retrieval result from the service, revision `00002` temporarily exposed a diagnostic API `retrieve_ids` (retrieval only: no LLM call, nothing stored). It was **removed** in the final image `v2` (revisions `00003` and `00004`); `view_api` on the final service lists only `/ask`, and calling `/retrieve_ids` fails. Raw results for the run that used it: `remote_results_with_diagnostic_endpoint.json`.

## Summary

| # | Check | Result |
|---|---|---|
| 1 | Prompt parity (SHA-256 of STRICT_V2) | **PASS**. App and notebook both `e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a` (2244 characters); `REFUSAL_SENTENCE` equal |
| 2 | Embedding parity | **PASS**. 20 random chunks of at most 500 characters (207 of 985 qualify; the diagnostic endpoint cut text at 500 characters), seed 7. Minimum cosine **1.000000**; all 20 return themselves as top-1 (squared L2 distance 0.0 when rounded to 6 decimals) |
| 3 | Retrieval parity vs `06_Retrieval` | **PASS. 24 of 24** questions have identical top-5 chunk ids in identical order. Largest distance difference 4.9e-05 (the sheet stores 4 decimals) |
| 4 | Answer sanity vs saved STRICT_V2 | **Mostly pass, one real difference**: 16 of 16 answerable questions answered; 7 of 8 unanswerable questions refused (UNANS-01 did not, see below); 18 of 24 answers word-for-word identical to the saved ones; mean text similarity 0.921; refusal-sentence start matches the saved answer for 24 of 24 |
| 5 | UI smoke test | **PASS** with notes (below) |

Check 2 note: the cosine is derived from the service's squared L2 distance (`cos = 1 - d/2` for unit vectors) between a chunk's text and its stored vector, not from a direct vector-to-vector comparison. Text is embedded with newlines replaced by spaces, exactly as `HuggingFaceEmbeddings` did when the stored vectors were made. Normalisation comes from bge-m3's own pipeline, not from a flag.

Check 3 note: the notebook used Chroma (HNSW, approximate). The app uses exact squared-L2 search in numpy with a stable sort (ties go to the lower chunk id). No tie or approximation difference showed up on the 24 questions.

## Check 4 in detail

Responses for the 24 questions came from the service (`check4_responses.jsonl`) and were compared with the 24 saved `STRICT_V2` responses (`check4_results.json`).

- **Identical to saved:** 18 of 24. The 6 that differ: HRSD-Q1 (wording), RES310-Q3 (wording), OWWA-Q2 (tiny wording), RA8042-Q4 (tiny wording), UNANS-05 (wording and language of the second sentence), **UNANS-01 (substance)**.
- **Answerable (16):** all answered, none started with the refusal sentence.
- **Unanswerable (8):** 7 start with the refusal sentence. UNANS-01 does not.
- **UNANS-01 (real difference).** The saved answer said the Standard Employment Contract leaves the monthly salary blank (`$____`). The hosted answer says the contract states a minimum monthly salary of US$200 and cites `POEA_MC19_1999_SupplementaryGuidelines_KSA.txt`. The US$200 figure is in that circular, but the answer attributes it to the contract, which is the mistake the evaluation set was designed to catch. Repeated 3 times on the service: same answer each time.
  - Cause investigated: retrieval ids match the log (check 3), and the prompt hash matches (check 1). I rebuilt the exact message from the logged chunk ids and sent it to Groq from the PC: **1,472 prompt tokens, identical to the 1,472 recorded in the notebook run**, and the answer was again the US$200 one (2 of 2 runs). So the input is the same and the model now answers differently: Groq's `openai/gpt-oss-20b` behaved differently from when the notebook was run, even at temperature 0. This is not caused by the hosting code.
- **Language heuristic.** A crude Tagalog-word count flagged 4 of 24 (UNANS-02, -06, -07, -08) as "language not matching". All four answers are word-for-word identical to the saved ones. They show the known limitation (the sentence after the refusal can be in a different language than the question). Language was OK for the other 20.
- **Non-determinism elsewhere.** In the later smoke test HRSD-Q1 returned the saved wording instead of the wording seen in check 4, so wording varies from run to run even at temperature 0.
- **Generation latency per question through the service (warm):** mean 4.62 s, max 8.47 s (n = 24, last attempt of each question; the pacer sometimes made the first attempt answer "busy", after which the script waited and retried).

## Check 5 in detail

Through the public URL with `gradio_client` (revision `00003`, final image):

| Case | Result |
|---|---|
| English question | Answered, Sources shown, 5 retrieved passages; 22.7 s for this first call (included an instance start), later calls 2.5 to 7.2 s |
| Taglish question | Taglish answer, Sources, 5 passages; 2.5 s |
| Unanswerable question (weather in Riyadh) | Refusal sentence, Sources, 5 passages; 7.2 s |
| Empty input | "Please type a question first." |
| 600-character input | Rejected on the server: "Your question is 600 characters long. Please keep it under 500 characters." |
| Key missing | Tested in a local child process with `GROQ_API_KEY` removed from that process only (retrieval stubbed because the model cannot load on the PC): "The assistant is not set up yet: the Groq API key is missing on the server..." and no stack trace. The wording was then changed from "Space owner" to "service owner" in the final image |

Browser check (Playwright at 390 x 844): the page renders on a warm service with title, notice, chat box, Ask button, six examples and About. A Taglish question returned an answer with Sources and an expandable "Retrieved passages" list with rank, file, page and escaped excerpt. Screenshot: `ui_answer_mobile.png`.

Usability note: the question box has two lines, so Enter adds a new line and Shift+Enter or the Ask button sends the question.

## Problems found during deployment (be aware)

1. **Startup race (fixed in image `v3`).** With image `v2`, Gradio's `launch()` checked that it could reach itself on localhost. In the logs, 1 of 6 instance starts raised `ValueError: When localhost is not accessible...`, the container exited and Cloud Run started a new one. Visitors who hit that instance saw a 503 or a blank page and then a wait of about 26 s. Image `v3` serves the app with uvicorn (`gr.mount_gradio_app`) instead of `launch()`; see the final section.
2. **Concurrency.** Cloud Run `--concurrency` was changed from 2 to 10 after a browser load showed static files failing with "request was aborted after waiting too long for an available instance" while a second instance was starting. The app still limits itself to 2 concurrent questions.

## Differences from the notebook

| Area | Notebook | Hosted |
|---|---|---|
| Vector search | Chroma, HNSW, squared L2 | Exact numpy squared L2, stable sort. 24 of 24 identical top-5 |
| Embedding device | GPU | CPU (Cloud Run); minimum cosine 1.0 on the sample |
| Pacing and retries | Waits up to 60 s, up to 6 retries | A request waits at most 8 s for the pacer or one Groq retry, then shows "The assistant is busy, please try again in a minute." |
| Question length | Unlimited | 500 characters, enforced on the server; 1 question per 4 s per session |
| Model behaviour | Run on the notebook day | Groq output has changed for at least UNANS-01 (see above); 18 of 24 answers identical |
| Context format | `page 12` | Same: pages are converted to integers before building the context |
| Hosting | n/a | Cloud Run 4 Gi, 2 vCPU, min 0 / max 2 instances, concurrency 10 (not 2) |
| Chat memory | None | None (each question independent) |

## Final revision (image v3, revision 00005-bav)

Change from image `v2`: only the last lines of `app.py` (served with uvicorn and `gr.mount_gradio_app` instead of `demo.launch()`). Prompt, model, data and retrieval code are unchanged. `app.py` SHA-256: `ea6778fc9f0d3e176cf57ffee852d2eb9a605622207ec97a74a5ee464bd03763` (`app_py_sha256_v3.txt`).

**Rollout.** Deployed as a tagged revision with 0% traffic, tested, then switched to 100%; the `v2` revision stays available as `v2rollback`.

**Startup stability test.** 9 fresh container starts of image `v3` (the tagged revision plus 8 throwaway no-traffic revisions of the same image, script `start_test.sh`): **0 crashes**. All 9 reached "Application startup complete" with no `Traceback` or `ValueError`; start times 55, 44, 49, 48, 50, 46, 47, 60, 49 s; each tag URL answered `/` and `/config` with HTTP 200. The old image crashed on 1 of 6 starts, so 0 of 9 is consistent with the fix but not proof by itself (it would happen about 1 time in 5 by chance at the old rate); the check that used to fail no longer exists in the code.

**Checks re-run on the live final revision** (public URL, through `gradio_client`; `final_checks.py`, `remote_checks.py`; raw data in `final_v3_results.json`, `final_v3_responses.jsonl`, `remote_results_final_v3.json`):

| # | Check | Result |
|---|---|---|
| 1 | Prompt parity | **PASS**. `STRICT_V2` taken from the `app.py` that was built into the image has SHA-256 `e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a`, equal to the notebook's own prompt cell |
| 3 | Retrieval parity | **PASS. 24 of 24.** The diagnostic endpoint no longer exists, so the check compared the "Retrieved passages" block that every answer shows (rank, source, page and the 400-character excerpt, for all 5 ranks) with what the chunk ids logged in `06_Retrieval` would produce. All 24 questions are identical in content and order |
| 4 | Answers | 16 of 16 answerable questions answered; 7 of 8 unanswerable questions refused (UNANS-01 again gives the US$200 answer, same cause as above); **17 of 24 identical** to the saved answers, mean text similarity 0.896. The questions that differ are not the same as in the earlier run (this time HRSD-Q1, RES310-Q3, BIL-Q2, CONTACT-Q3, UNANS-01, UNANS-05, UNANS-06), which again shows wording varies from run to run. Per-question time through the service: mean 5.73 s, max 27.92 s (the max is the first question on a cold instance); about 4.7 s without it |
| 5 | UI smoke test | **PASS**. English 1.63 s, Taglish 2.24 s and unanswerable 7.16 s, each with Sources and 5 passages; empty input gives "Please type a question first."; the 600-character input is rejected on the server |

Check 2 (embedding parity) was not repeated on `v3`: the embedding code and data are byte-identical to `v2` and the diagnostic endpoint that made it possible is gone. Retrieval parity (check 3) depends on the embeddings, and it passes 24 of 24.

**Browser check of the final revision (390 x 844).** After the instance is up, the page, a question, the answer, Sources and the expanded "Retrieved passages" render correctly (`ui_final_v3_mobile.png`). On a cold service the browser shows only "Loading..." until the instance has started: one request to the live URL waited 58.4 s according to the Cloud Run log. Two of my browser tests timed out at 30 s for this reason before I understood it; they were not crashes.

**Differences from the notebook, updated.** Same as the table above, plus: the app is served by uvicorn instead of `launch()`; the live concurrency is 10; and `00013-fof`, a leftover no-traffic test revision that Cloud Run will not delete because it is the newest, remains in the service (cost: none).


## Image v4 (new UI), revision 00016-qaz, live from 2026-11-11

Presentation-only change (`app.py` UI section, new `style.css`); see HOSTING_NOTES.md for the design changes and the v3 rollback command. `app.py` SHA-256 `07a965251b9211d9ea23595b1b8a1d99bcaa2ca1ff1d4ef05f1dacd5c4fdcda2`.

**Local (Playwright, stub model/Groq; `ui_test.py`, `ui_v4_local_results.json`):** 390 px and 1280 px, light and dark: no horizontal overflow, no tap target under 44 px, text contrast 6.96 to 16.99 (light) and 7.86 to 13.84 (dark), visible focus ring (3 px), Enter sends, Shift+Enter adds a line, chip fills the box with the full question, waiting text and 3 dots shown, 0 third-party requests. Screenshots: `ui_v4_light.png`, `ui_v4_dark.png`, `ui_v4_mobile.png`, `ui_v4_desktop.png`, `ui_v4_loading.png`, `ui_v4_answer_sources.png`, live page `ui_v4_live_390.png`.

**On the tagged revision (0% traffic) before the switch:**

| Check | Result |
|---|---|
| Prompt hash (from the `app.py` built into the image) | PASS, `e5236f33...650d6a` |
| `view_api` | PASS, only `/ask` |
| Retrieval vs saved | 10 of 10 questions that were answered match (rank, source, page, excerpt). **Not completed: 14 of 24.** 6 were asked but Groq said "busy" 8 times each, 8 were not run |
| Empty input / 600 characters | PASS ("Please type a question first." / rejected on the server) |
| English, Taglish, unanswerable smoke test | **Not completed.** Groq returned "busy" (quota/rate limit); the earlier run's results file was a stale copy because the script crashed on a Windows print encoding error |
| Browser at 390 px with a real answer + waiting state on the real service | **Not completed** (no answer could be produced while Groq was busy). Live page load at 390 px checked after the switch: renders, no overflow, 6 chips |
| 3 cold starts | **Not done** (each needs 15 minutes idle) |
| 24 answers identical to saved | **Not measured** (v3 baseline: 17 of 24) |

**Decision:** traffic was moved to v4 on the owner's explicit instruction to stop waiting, although the remaining answer-based checks were not finished. The server code path for answers is unchanged apart from class names on the passages block and the waiting message, and the 10 answered questions rendered with Sources and 5 passages. Still to confirm when Groq's limit resets: one real question in a browser (answer, Sources, passages, waiting text).
