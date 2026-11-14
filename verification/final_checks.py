"""Final-revision checks that need no diagnostic endpoint.
Run: python final_checks.py <service_url> <eval_question_set.csv> <out_prefix>
 - check 1: SHA-256 of the STRICT_V2 text in app.py (the file built into the image) vs the notebook's own prompt cell
 - check 3: for each of the 24 questions, ask the service and compare the 'Retrieved passages' block (rank, source, page, 400-char excerpt)
            with what the chunk ids logged in 06_Retrieval would produce. Identical source+page+excerpt for all 5 ranks = same chunk and order.
 - check 4 data: the 24 answers are saved so they can be compared with the saved STRICT_V2 answers again
Needs no model on this PC and no secret."""
import sys, json, time, html, re, hashlib
from pathlib import Path

import pandas as pd
from gradio_client import Client

HERE = Path(__file__).parent
URL, QCSV, PREFIX = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, str(HERE.parent))
LOGS = r"D:\Final Project\Next Run v2\Goats_Experiment_Logs.xlsx"
NOTEBOOK = r"D:\Final Project\Next Run v2\Goats_RAG_Chatbot_Source_Code_ran.ipynb"
res = {}

# ---- check 1 (reads app.py text only; does not import the model code path)
app_src = (HERE.parent / "app.py").read_text(encoding="utf-8")
ns_app = {"__name__": "x"}
start = app_src.index("REFUSAL_SENTENCE =")
end = app_src.index("# ---------------------------------------------------------------- index")
ns_a = {"DOMAIN_NAME": ""}
exec(app_src[start:end], ns_a)
nb = json.load(open(NOTEBOOK, encoding="utf-8"))
cell = next("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code" and 'REFUSAL_SENTENCE = "' in "".join(c["source"]))
ns_n = {"DOMAIN_NAME": "household service worker (HSW) rights and overseas employment in Saudi Arabia"}
exec(cell[cell.index("REFUSAL_SENTENCE ="):cell.index("PROMPT_LABEL")], ns_n)
h_app = hashlib.sha256(ns_a["PROMPTS"]["STRICT_V2"].encode("utf-8")).hexdigest()
h_nb = hashlib.sha256(ns_n["PROMPTS"]["STRICT_V2"].encode("utf-8")).hexdigest()
res["check1"] = {"app_py_sha256": hashlib.sha256(app_src.encode("utf-8")).hexdigest(), "app_prompt_sha256": h_app, "notebook_prompt_sha256": h_nb, "equal": h_app == h_nb}
print("check1", res["check1"], flush=True)

# ---- check 3 through the answer's passages block
questions = pd.read_csv(QCSV, encoding="utf-8-sig")
chunks = [json.loads(l) for l in (HERE.parent / "data" / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
ref = pd.read_excel(LOGS, sheet_name="06_Retrieval")
client = Client(URL, verbose=False)
BUSY = ("The assistant is busy", "Please wait")


def expected(cid, rank):
    c = chunks[cid]
    page = int(c["Page"]) if c.get("Page") == c.get("Page") and c.get("Page") is not None else None
    return {"rank": rank, "source": c["Source"], "page": page, "excerpt": " ".join(c["Text"].split())[:400]}


def parse(reply):
    out = []
    for m in re.finditer(r"<li><b>(.*?)</b> \(rank (\d+)\)<br>(.*?)</li>", reply, re.S):
        head = html.unescape(m.group(1))
        pm = re.match(r"(.*), page (\d+)$", head)
        out.append({"rank": int(m.group(2)), "source": pm.group(1) if pm else head, "page": int(pm.group(2)) if pm else None,
                    "excerpt": html.unescape(m.group(3))})
    return out


rows, match, lat = [], 0, []
out_file = HERE / f"{PREFIX}_responses.jsonl"
if out_file.exists():
    out_file.unlink()
for q in questions.itertuples():
    for attempt in range(8):
        time.sleep(5)
        t = time.perf_counter()
        hist, _ = client.predict(q.Question, [], api_name="/ask")
        secs = time.perf_counter() - t
        content = hist[-1]["content"]
        reply = "".join(b.get("text", "") for b in content) if isinstance(content, list) else content
        if reply.startswith(BUSY):
            time.sleep(35)
            continue
        break
    got = parse(reply)
    want_ids = [int(x) for x in ref[ref.Eval_ID == q.Eval_ID].sort_values("Rank").Chunk_ID]
    want = [expected(cid, i) for i, cid in enumerate(want_ids, start=1)]
    ok = got == want
    match += ok
    lat.append(secs)
    rows.append({"Eval_ID": q.Eval_ID, "match": ok, "passages_found": len(got), "log_ids": want_ids})
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({"Eval_ID": q.Eval_ID, "Response": reply.split("\n\n**Sources**")[0], "latency_s": round(secs, 2), "attempts": attempt + 1}, ensure_ascii=False) + "\n")
    print(q.Eval_ID, "retrieval match" if ok else "MISMATCH", round(secs, 1), "s", flush=True)
res["check3_via_passages"] = {"questions": len(rows), "exact_matches": match, "mean_latency_s": round(sum(lat) / len(lat), 2), "max_latency_s": round(max(lat), 2), "rows": rows}
print("check3", match, "/", len(rows), flush=True)
(HERE / f"{PREFIX}_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
