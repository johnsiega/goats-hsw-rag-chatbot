"""Checks 1-3: prompt parity, embedding parity, retrieval parity. Run: python checks_1_to_3.py <eval_question_set.csv>
Reads the notebook and the experiment log read-only. Writes check1_3_results.json next to this script."""
import sys, json, hashlib, random
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import app

NOTEBOOK = r"D:\Final Project\Next Run v2\Goats_RAG_Chatbot_Source_Code_ran.ipynb"
LOGS = r"D:\Final Project\Next Run v2\Goats_Experiment_Logs.xlsx"
questions = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
res = {}

# ---- 1. prompt parity: execute the notebook's own prompt cell and hash STRICT_V2
nb = json.load(open(NOTEBOOK, encoding="utf-8"))
cell = next("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code" and 'REFUSAL_SENTENCE = "' in "".join(c["source"]))
src = cell[cell.index("REFUSAL_SENTENCE ="):cell.index("PROMPT_LABEL")]
ns = {"DOMAIN_NAME": app.DOMAIN_NAME}
exec(src, ns)
nb_hash = hashlib.sha256(ns["PROMPTS"]["STRICT_V2"].encode("utf-8")).hexdigest()
app_hash = hashlib.sha256(app.PROMPTS["STRICT_V2"].encode("utf-8")).hexdigest()
res["check1"] = {"notebook_sha256": nb_hash, "app_sha256": app_hash, "equal": nb_hash == app_hash,
                 "refusal_equal": ns["REFUSAL_SENTENCE"] == app.REFUSAL_SENTENCE, "chars": len(app.PROMPTS["STRICT_V2"])}
print("check1", res["check1"])

# ---- 2. embedding parity: 20 random chunks re-embedded vs stored vectors
random.seed(7)
ids = random.sample(range(len(app.CHUNKS)), 20)
vecs = np.stack([app.embed_text(app.CHUNKS[i]["Text"]) for i in ids])
stored = app.VECTORS[ids]
cos = (vecs * stored).sum(1) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(stored, axis=1))
res["check2"] = {"n": 20, "min_cosine": float(cos.min()), "mean_cosine": float(cos.mean()), "chunk_ids": ids,
                 "query_vector_norm": float(np.linalg.norm(vecs[0]))}
print("check2", res["check2"])

# ---- 3. retrieval parity vs 06_Retrieval
ref = pd.read_excel(LOGS, sheet_name="06_Retrieval")
rows, match, dmax = [], 0, 0.0
for q in questions.itertuples():
    items = app.retrieve(q.Question)
    got = [int(i["id"]) for i in items]
    r = ref[ref.Eval_ID == q.Eval_ID].sort_values("Rank")
    want = [int(x) for x in r.Chunk_ID]
    dd = float(np.max(np.abs(np.array([i["distance"] for i in items]) - r.Distance.to_numpy()))) if got == want else None
    if dd is not None:
        dmax = max(dmax, dd)
    ok = got == want
    match += ok
    rows.append({"Eval_ID": q.Eval_ID, "match": ok, "app_top5": got, "log_top5": want, "same_set": sorted(got) == sorted(want),
                 "max_abs_dist_diff": dd})
res["check3"] = {"questions": len(rows), "exact_matches": match, "max_abs_distance_diff_on_matches": dmax, "rows": rows}
print("check3", match, "/", len(rows), "max dist diff", dmax)
for r in rows:
    if not r["match"]:
        print("MISMATCH", r)
(HERE / "check1_3_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
