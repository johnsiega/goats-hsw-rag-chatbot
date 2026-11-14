"""Mock-only test of the Groq -> OpenRouter fallback. Run: python verification\test_fallback.py
Does not import app.py (that would load bge-m3 and gradio); it extracts the needed functions with ast."""
import ast
import contextlib
import hashlib
import io
import json
import os
import time
import unittest.mock as mock
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app.py"
src = APP.read_text(encoding="utf-8")
ns = {"os": os, "json": json, "time": time, "urllib": urllib, "GROQ_MODEL": "openai/gpt-oss-20b", "GROQ_TEMPERATURE": 0,
      "GROQ_MAX_COMPLETION_TOKENS": 1500, "GROQ_REASONING_EFFORT": "low", "GROQ_TIMEOUT_S": 45, "MAX_WAIT_S": 8}
for n in ast.parse(src).body:
    if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ("Busy", "call_openrouter_once", "call_groq"):
        exec(compile(ast.Module(body=[n], type_ignores=[]), str(APP), "exec"), ns)
Busy, call_groq = ns["Busy"], ns["call_groq"]
ns["pacer"] = mock.Mock()

MSGS = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "Q"}]
sent = []


class Resp:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def read(self, *a): return self.body


def fake_urlopen(req, timeout):
    sent.append((req, timeout))
    return Resp(b'{"choices":[{"message":{"content":"OR"}}],"usage":{"prompt_tokens":2,"completion_tokens":3}}')


def groq_fails(reason):
    def f(m, w): raise Busy(reason)
    return f


def run(env, direct):
    ns["_call_groq_direct"] = direct
    out = io.StringIO()
    with mock.patch.dict(os.environ, env), mock.patch.object(urllib.request, "urlopen", fake_urlopen), contextlib.redirect_stdout(out):
        return call_groq(MSGS), out.getvalue()


for k in ("FORCE_GROQ_FAIL", "OPENROUTER_API_KEY"):
    os.environ.pop(k, None)

# 1. primary path unchanged: Groq answer returned, OpenRouter never called, hook inert by default
sent.clear()
r, log = run({"OPENROUTER_API_KEY": "k"}, lambda m, w: {"text": "PRIMARY"})
assert r["text"] == "PRIMARY" and not sent and "fallback" not in log
# FORCE_GROQ_FAIL set to anything but "1" is inert
r, log = run({"OPENROUTER_API_KEY": "k", "FORCE_GROQ_FAIL": "0"}, lambda m, w: {"text": "PRIMARY"})
assert r["text"] == "PRIMARY" and not sent

# 2. rate / daily / connection failures retry ONCE through OpenRouter with the exact body
for reason in ("rate", "daily", "connection"):
    sent.clear()
    r, log = run({"OPENROUTER_API_KEY": "k"}, groq_fails(reason))
    assert r["text"] == "OR" and len(sent) == 1 and log.strip() == "fallback used", reason
    req, timeout = sent[0]
    body = json.loads(req.data)
    assert body == {"model": "openai/gpt-oss-20b", "messages": MSGS, "temperature": 0, "max_completion_tokens": 1500,
                    "reasoning": {"effort": "low"}, "provider": {"order": ["groq"], "allow_fallbacks": False}}, body
    assert req.full_url == "https://openrouter.ai/api/v1/chat/completions" and timeout == 45
    assert req.get_header("Authorization") == "Bearer k"
    assert "k" not in log.replace("fallback used", "")      # no secret in the log

# 3. forced failure hook: env var 1 skips Groq entirely
called = []
sent.clear()
r, log = run({"OPENROUTER_API_KEY": "k", "FORCE_GROQ_FAIL": "1"}, lambda m, w: called.append(1) or {"text": "PRIMARY"})
assert r["text"] == "OR" and not called and len(sent) == 1

# 4. no fallback for pacer / other errors; no key -> friendly Busy; OpenRouter failure -> Busy, no second attempt
for reason in ("pacer", "error"):
    sent.clear()
    try:
        run({"OPENROUTER_API_KEY": "k"}, groq_fails(reason))
        raise AssertionError("fell back on " + reason)
    except Busy as e:
        assert str(e) == reason and not sent
try:
    run({}, groq_fails("daily")); raise AssertionError("no key must raise")
except Busy:
    pass
for bad in (b"not json", b'{"choices":[{"message":{"content":""}}]}'):
    sent.clear()
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "k"}), mock.patch.object(
            urllib.request, "urlopen", lambda req, timeout, b=bad: sent.append(1) or Resp(b)):
        ns["_call_groq_direct"] = groq_fails("rate")
        try:
            call_groq(MSGS); raise AssertionError("bad response must raise")
        except Busy as e:
            assert str(e) == "fallback failed" and len(sent) == 1

# 5. the prompt is unchanged
ns2 = {"DOMAIN_NAME": ""}
exec(src[src.index("REFUSAL_SENTENCE ="):src.index("# ---------------------------------------------------------------- index")], ns2)
h = hashlib.sha256(ns2["PROMPTS"]["STRICT_V2"].encode()).hexdigest()
assert h == "e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a", h

# 6. the hook is read from the environment only (no request/UI path)
assert src.count("FORCE_GROQ_FAIL") == 1
print("test_fallback: ALL PASS; prompt sha256", h)
