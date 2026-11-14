# Goats HSW Rights Chatbot

A retrieval-augmented chatbot (English and Taglish) about the rights of Filipino household service workers in Saudi Arabia. It answers only from 16 official Philippine and Saudi documents and shows its sources under every answer.

**Live app:** https://goats-hsw-rag-chatbot-626564095782.asia-southeast1.run.app

**General information from official Philippine and Saudi documents. Not legal advice. It can be incomplete or wrong.**

- Embeddings: BAAI/bge-m3 (chunks 800 / overlap 100, top-5, exact L2 search in numpy)
- Answer model: `openai/gpt-oss-20b` on Groq, prompt `STRICT_V2`, one question at a time (no chat memory)
- If the direct Groq request is rate-limited or unavailable, the app retries once through OpenRouter, pinned to Groq with provider fallbacks disabled
- Needs `GROQ_API_KEY` and `OPENROUTER_API_KEY` as environment variables; never commit their values
- Questions and answers are not logged or stored by the app. When fallback is used, the question and retrieved passages are processed by OpenRouter and routed to Groq

## Run locally

The included `BAAI/bge-m3` embeddings and retrieval data require substantial memory. After installing `requirements.txt`, set the API keys in your environment and run:

```powershell
python app.py
```

The fallback unit test uses mocks and does not load the embedding model:

```powershell
python verification/test_fallback.py
```

Deployment and verification details are documented in `HOSTING_NOTES.md` and `verification/report.md`.

ITC 508, Jose Rizal University, Group Goats
