"""Real OpenRouter request using app.py's fallback code, with the primary forced to fail.

Requires OPENROUTER_API_KEY in the environment. Prints no key, question, answer or error body.
Does not import app.py or load the embedding model.
"""
import ast
import collections
import hashlib
import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
ns = {"os": os, "json": json, "time": time, "urllib": urllib, "re": re,
      "collections": collections, "threading": threading, "Path": Path}
exec(source[source.index("# ---- final chatbot configuration"):source.index("# ---------------------------------------------------------------- index")], ns)
assert hashlib.sha256(ns["PROMPTS"]["STRICT_V2"].encode()).hexdigest() == "e5236f33c55a8660c601223ff3f2979f407fe25d14799e3b3e0e889c48650d6a"
tree = ast.parse(source)
for node in tree.body:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in (
        "Busy", "TokenPacer", "call_openrouter_once", "call_groq"
    ):
        exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), ns)
ns["pacer"] = ns["TokenPacer"](6000, 3)
ns["_call_groq_direct"] = lambda messages, max_wait: (_ for _ in ()).throw(ns["Busy"]("daily"))
chunks = [json.loads(line) for line in (Path(__file__).resolve().parent.parent / "data" / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
question = "How many professions fall within the scope of domestic workers under the HRSD guide?"
items = [c for c in chunks if "HRSD" in (c.get("Source") or "")][:5]
assert len(items) == 5
context = "\n\n".join(f"[Source {i}: {c['Source']}" + (f", page {int(c['Page'])}" if c.get("Page") is not None else "") + f"]\n{c['Text']}" for i, c in enumerate(items, 1))
messages = [{"role": "system", "content": ns["PROMPTS"]["STRICT_V2"]},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"}]
try:
    out = ns["call_groq"](messages)
    assert out["text"] and out["prompt_tokens"] >= 0
    print("forced-failure OpenRouter path: PASS; provider pinned to Groq in request")
except Exception:
    print("forced-failure OpenRouter path: FAIL (error details withheld)")
    raise SystemExit(1)
