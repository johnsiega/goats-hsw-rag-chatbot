# Hosting notes: Goats HSW RAG chatbot

## v5: Groq to OpenRouter fallback (live since 2026-11-11)

**Live revision `goats-hsw-rag-chatbot-00019-van`** (image `v5`, digest `sha256:afaf1a7a0930ef8feb00116ca7c55008909e88d9cc4ac59ab2504bf5e9b89915`, tag `v5test`) at 100%. `app.py` SHA-256 `065aacf721961329e8726e36555235e5b5ecf774b75bfb282b6dc20989ae2e36`; prompt SHA-256 unchanged (`e5236f33...650d6a`); retrieval, UI, limits, settings (4Gi, 2 CPU, min 0, max 2, concurrency 10) and the `/ask` API unchanged. Env: `GRADIO_ANALYTICS_ENABLED=False`; secrets `GROQ_API_KEY:2` and `OPENROUTER_API_KEY:1` (both as environment variables).

- **Behaviour:** if the direct Groq call ends in a rate-limit, daily-limit or connection error, the app retries ONCE through OpenRouter (`openai/gpt-oss-20b`, same system prompt, temperature 0, same max tokens, reasoning effort low, provider routing pinned to Groq with fallbacks disabled). If that also fails, the visitor sees the usual "busy" message. Local pacer limits and missing-key errors do not trigger it. Answers may differ slightly.
- **Third-party processing:** when the fallback runs, the question and the retrieved passages are sent to **OpenRouter**, which routes them to Groq. Normal traffic goes to Groq directly.
- **Logging:** the app does not log questions or answers. The only new log line is the fixed text `fallback used`.
- **Test hook:** env var `FORCE_GROQ_FAIL=1` makes the Groq call fail artificially. It is read only from the server environment (no UI or API path), and is not set on the live revision.
- **Tests (3 live questions in total):** (1) throwaway revision `00018-xuq` (tag `fbtest`, `FORCE_GROQ_FAIL=1`, 0% traffic): answered with sources and the log showed `fallback used`; (2) `00019-van` as tag `v5test` before the switch: answered by the normal path, no `fallback` log line; (3) public URL after the switch: answered in 2.7 s. Mock test `verification/test_fallback.py` passes. The throwaway revision and tag `fbtest` were deleted.
- **Small additions vs the staged code:** a `User-Agent` header on the OpenRouter request and the `fallback used` log line.
- **Rollback to v4** (instant):
```
gcloud run services update-traffic goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --to-revisions goats-hsw-rag-chatbot-00016-qaz=100
```
- The Cloud Run runtime service account has `secretAccessor` on `OPENROUTER_API_KEY` (granted earlier). Build: `verification/build_v5.log` (11 min 34 s).

## What is deployed

| Item | Value |
|---|---|
| Platform | Google Cloud Run (service `goats-hsw-rag-chatbot`) |
| Project / region | `goats-hsw-rag-1110` / `asia-southeast1` |
| **Public URL** | https://goats-hsw-rag-chatbot-626564095782.asia-southeast1.run.app (also https://goats-hsw-rag-chatbot-edc7oz3psq-as.a.run.app) |
| Image (live) | `.../goats-hsw-rag-chatbot:v4` (digest `sha256:3064f98d1daa289dae2b1ccad1fa9da9589d88f9441d1935ab09d979c7594e8e`; `app.py` SHA-256 `07a965251b9211d9ea23595b1b8a1d99bcaa2ca1ff1d4ef05f1dacd5c4fdcda2`, `style.css` SHA-256 `4db12433e7748422533a0e3602547fd9e6ba8392b0a5f109725f8e4e0bfb30ce`). Previous: `v3` (digest `sha256:250878dfc65d13d3b94a11dc3b0809cc0b0dc8ad319582d28ce7fc5bc403e141`) |
| **Revision serving 100% of traffic** | `goats-hsw-rag-chatbot-00019-van` (image `v5`), tag `v5test`. Previous: `00016-qaz` (image `v4`), tag `v4test` |
| Previous revision (v3) | `goats-hsw-rag-chatbot-00005-bav`, tag `v3test`, 0% traffic |
| Rollback revision | `goats-hsw-rag-chatbot-00004-9pb` (image `v2`, launched with `demo.launch()`), tag `v2rollback`, 0% traffic |
| Settings | `--memory 4Gi --cpu 2 --cpu-boost --min-instances 0 --max-instances 2 --concurrency 10 --timeout 300 --allow-unauthenticated` |
| Environment | `GRADIO_ANALYTICS_ENABLED=False`; `GROQ_API_KEY` mounted from Secret Manager secret `GROQ_API_KEY`, **version 2** (version 1 is disabled) |
| Runtime service account | `626564095782-compute@developer.gserviceaccount.com`, with `secretmanager.secretAccessor` on that one secret only |
| Pinned versions (tested) | Python 3.13 (image `python:3.13-slim`), gradio 6.31.0, sentence-transformers 6.2.0, transformers 5.22.1, torch 2.15.0 CPU, numpy 2.5.4, groq 1.7.0 |
| Model | BAAI/bge-m3, downloaded into the image at build time; `HF_HUB_OFFLINE=1` at run time |
| Data in the image | `data/chunks.jsonl` (985 chunks), `data/embeddings.npy` (985 x 1024) |

Not used: Hugging Face. The first plan was a free Hugging Face Space, but creating it failed with `402 Payment Required` (free Gradio Spaces need PRO). Nothing was created on Hugging Face. `README.md` in this folder is the Space card that was written for that plan; it is not used by Cloud Run.

## Changes from the first Cloud Run command

- **Concurrency changed from 2 to 10.** With 2, a browser page load (about 25 parallel requests for scripts and styles) overflowed the instance while a second one was starting; Cloud Run aborted the waiting requests with "request was aborted after waiting too long for an available instance" and the page stayed blank. The app limits itself anyway: 2 questions at a time, a queue of 20, 1 question per 4 s per session, and a Groq token pacer (6000 tokens per minute). `--min-instances 0` was kept.
- **Diagnostic endpoint removed.** `retrieve_ids` (used only to run checks 2 and 3 from outside the container) exists in image `v1` and revision `00002` only; image `v2` does not contain it.
- **Error message wording** changed from "Space owner" to "service owner".
- **Startup race fixed with image `v3`.** With image `v2`, 1 of 6 instance starts crashed about 10 s after "Running on local URL" with `ValueError: When localhost is not accessible...`, raised by Gradio's self-check inside `demo.launch()`. Visitors who hit that instance saw a 503, a blank page, or an extra wait of about 30 s. `v3` serves the same Gradio app through uvicorn (`gr.mount_gradio_app(FastAPI(), demo, path="/", css=CSS, show_error=False)` and `uvicorn.run`) and has no such check. Only the last lines of `app.py` changed; the prompt, model, data and retrieval code are untouched.
  - **Test before the switch:** `v3` was deployed as a tagged revision with 0% traffic (`00005-bav`). Then 8 more fresh container starts were made by deploying 8 throwaway no-traffic revisions of the same image (only a `NONCE` environment variable differed; script `verification/start_test.sh`). All 9 starts reached "Application startup complete" with no `Traceback`, `ValueError` or error in the logs, and each tag URL answered `/` and `/config` with 200. Start times were 55, 44, 49, 48, 50, 46, 47, 60 and 49 s.
  - **How much that proves:** the earlier crash rate was 1 in 6; 0 in 9 is consistent with the fix but would also happen by chance about 1 time in 5 at that rate. The reason for believing in the fix is that the check that failed no longer exists. Watch the logs after switching (command below).
  - **Cleanup:** 7 of the 8 throwaway revisions were deleted. `00013-fof` is the newest revision and Cloud Run refuses to delete the newest revision directly; it has 0% traffic and no instance, so it costs nothing. It also means the service template still carries the harmless variable `NONCE=8`; add `--remove-env-vars NONCE` to the next deploy.

## v4: new look (UI only)

Switched to 100% on 2026-11-11. Same prompt (SHA-256 `e5236f33...650d6a`), retrieval, model, limits and `/ask` contract; only the presentation changed.

- **Design:** glass header and input bar (`backdrop-filter`, solid fallback), rounded cards, one-accent tonal palette (hue 185, light and dark, follows the system setting), pill example chips (scroll sideways, tap fills the box), large rounded input bar fixed at the bottom, "Retrieved passages" as a bottom-sheet-like panel (`<details class="sheet">`), Sources as chips, fade/slide animations (off with reduced-motion), system font stack.
- **Waiting state:** animated dots. The first answer after a start shows "Waking up the assistant, the first answer can take up to a minute."; later ones show "Searching the documents...". The 45 to 60 s Cloud Run cold start happens before any page is served, so it **cannot be restyled**; the page stays blank/"Loading..." until the instance is up.
- **Enter sends, Shift+Enter adds a new line** (single-line box that grows to 5 lines). The old "Enter adds a new line" limitation no longer applies.
- Hidden: Gradio footer and the chat toolbar (its share button targets Hugging Face). Chips replace `gr.Examples`; they add no API endpoint (`view_api` lists only `/ask`).
- New file `style.css` (added to `Dockerfile` and `.dockerignore`). Gradio still requests its own bundled SourceSansPro file from the same server (no third-party request).
- Build 9 min 44 s. The deploy command no longer includes `--remove-env-vars NONCE`: `--set-env-vars` already replaces all variables.

**Roll back to v3** (instant, no rebuild):
```
gcloud run services update-traffic goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --to-revisions goats-hsw-rag-chatbot-00005-bav=100
```

## Cold start

After the service has been idle (about 15 minutes), the next visitor starts a new instance. What a visitor sees, in seconds:

- **Instance start until the page can load: about 42 to 60 s** (container start plus loading the 2.3 GB model). Measured from the logs: 6 starts of image `v2` (58, 47, 49, 48, 42, 55 s) and 9 starts of image `v3` (55, 44, 49, 48, 50, 46, 47, 60, 49 s). A page request that arrives during this time waits for it: on 2026-11-10 at 13:24 UTC a real browser request to the live URL waited **58.4 s** (logged by Cloud Run) while the page showed only "Loading..." and nothing else. Wait at least a minute on a cold service before concluding it is broken.
- **First question on a fresh instance: about 22 to 25 s** (22.6, 22.7 and 24.7 s measured), against **2 to 8 s** for later questions (warm: 2.2 s when the same Taglish question was asked again, mean 4.6 s and max 8.5 s over the 24 evaluation questions). The extra time is the first embedding run reading the model weights from disk into memory.
- **So the first answer after idle takes roughly 65 to 80 s** from a standing start. A warm page load takes about 0.1 s.

Caveat: I did not get a clean "idle then one visitor" run, because the browser tab I used for the UI check stayed open and kept waking the service; the figure above is built from the 6 startup log times plus the measured first-question times. An open Gradio tab also keeps an instance alive, so a service that is being watched will not scale to zero.

## How to redeploy

From `D:\Final Project\hosted_app` in PowerShell (project `goats-hsw-rag-1110` must be the target). Use a new image tag each time (next: `v4`):

```
gcloud builds submit . --project goats-hsw-rag-1110 --region asia-southeast1 --tag asia-southeast1-docker.pkg.dev/goats-hsw-rag-1110/goats/goats-hsw-rag-chatbot:v4 --timeout 2400s
gcloud run deploy goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --image asia-southeast1-docker.pkg.dev/goats-hsw-rag-1110/goats/goats-hsw-rag-chatbot:v4 --no-traffic --tag canary --memory 4Gi --cpu 2 --cpu-boost --min-instances 0 --max-instances 2 --concurrency 10 --timeout 300 --allow-unauthenticated --set-env-vars GRADIO_ANALYTICS_ENABLED=False --remove-env-vars NONCE --set-secrets GROQ_API_KEY=GROQ_API_KEY:2
```

Test the tag URL printed by the deploy (allow about a minute for the first load), then switch traffic with `gcloud run services update-traffic goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --to-revisions <new revision name>=100`. Tag names need at least 3 characters.

A build takes about 10 minutes (the builds so far took 9 min 51 s, 10 min 32 s and 10 min 23 s).

**Roll back to image `v2`** (instant, no rebuild):
```
gcloud run services update-traffic goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1 --to-revisions goats-hsw-rag-chatbot-00004-9pb=100
```

**Check for startup crashes after a change** (Bash; shows starts and any traceback):
```
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="goats-hsw-rag-chatbot" AND (textPayload:"Starting new instance" OR textPayload:"Application startup complete" OR textPayload:"Traceback")' --project goats-hsw-rag-1110 --freshness 6h --order asc --format="value(timestamp,resource.labels.revision_name,textPayload)"
``` To change only a setting, use `gcloud run services update ...` (no rebuild). To rotate the key, add a new secret version, then deploy with `GROQ_API_KEY=GROQ_API_KEY:<new version>`.
To stop all use: `gcloud run services delete goats-hsw-rag-chatbot --project goats-hsw-rag-1110 --region asia-southeast1` (the image and the secret stay until deleted separately).

## Free-tier and cost behaviour

- **Scales to zero.** With `--min-instances 0` there is no cost while idle. About 15 minutes after the last request the instance stops, and the next visitor triggers a cold start (see above).
- **Public service.** `--allow-unauthenticated` means anyone with the URL can use it and spend the Groq quota. The only throttles are the app's queue, per-session cooldown, token pacer, `--max-instances 2`, and Groq's own limits.
- **Groq limits.** The free Groq tier has a tokens-per-minute and a daily limit for this model. When either is hit the app shows "The assistant is busy, please try again in a minute." (a daily-limit error is treated the same way). Each question uses roughly 1,500 to 3,500 tokens.
- **Cloud Run free allowance (from memory, not confirmed on the pricing page; check cloud.google.com/run/pricing).** Request-based billing is believed to include about 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests per month. This service uses 2 vCPU and 4 GiB per instance, so one instance-second consumes 2 vCPU-seconds and 4 GiB-seconds; both allowances run out at about 90,000 instance-seconds, roughly 25 hours of billed instance time per month. Billed time includes the 40 to 50 seconds of each cold start and the seconds each question takes (about 2 to 8 s, shared by up to 10 simultaneous requests).
- **Other costs.** Artifact Registry: about 0.5 GB free, then roughly 0.10 USD per GB-month (unconfirmed); the images are several GB, so expect cents per month. Cloud Build: the free minutes should cover a few builds. Secret Manager: a single secret with a few accesses is expected to be within or near the free tier.

### Budget alert

Console: Billing, then Budgets & alerts, then Create budget. Scope it to project `goats-hsw-rag-1110` (billing account `017C4E-F7C9B7-1D2F05`), set an amount such as 5 USD per month, and keep alerts at 50%, 90% and 100%. Add your email to the notifications. A budget alert only warns; it does not stop spending. Command-line alternative:
```
gcloud billing budgets create --billing-account=017C4E-F7C9B7-1D2F05 --display-name="goats-hsw-rag budget" --budget-amount=5USD --filter-projects=projects/goats-hsw-rag-1110 --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

## Privacy

Questions and answers are not logged or stored by the app and Gradio analytics are disabled. Since v5, when Groq is rate-limited the question and retrieved passages may be sent to OpenRouter (third party, routed to Groq). Cloud Run itself keeps request logs (URL, status, timing) in Cloud Logging, but question text is not in the URL. Retrieved passages are shown as escaped text, not raw HTML.

## Known limitations

- **Long first load.** After idle time, the first visitor sees "Loading..." for up to about a minute and then waits another 20 to 25 s for the first answer. Setting `--min-instances 1` would remove this but bills an always-on 2 vCPU / 4 GiB instance; it was not done.
- **Startup race:** fixed in image `v3` (see above); 0 crashes in 9 fresh starts.
- **Groq model drift.** `openai/gpt-oss-20b` on Groq no longer gives the saved answer for UNANS-01: it says the Standard Employment Contract states US$200 (which comes from POEA MC 19 of 1999) instead of saying the contract leaves the salary blank. The input is identical to the notebook run (1,472 prompt tokens in both). 17 to 18 of 24 saved answers are reproduced word for word, and which ones differ changes from run to run.
- The sentence after a refusal is sometimes in a different language than the question.
- It knows only the 16 documents; it has no memory between questions.
- Cold start of about 45 to 60 s (model load) after the service has been idle.
- The browser tab used for testing keeps the service awake while it is open, so a watched service does not scale to zero.
