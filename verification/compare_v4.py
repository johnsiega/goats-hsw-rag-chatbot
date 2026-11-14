"""Compare a *_responses.jsonl from final_checks.py with the saved STRICT_V2 answers. usage: python compare_v4.py <responses.jsonl> <out.json>"""
import sys, json, difflib
saved = {}
for l in open(r"D:\Final Project\Next Run v2\eval_responses.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        if r["Prompt_ID"] == "STRICT_V2":
            saved[r["Eval_ID"]] = r["Response"]
REFUSAL = "I cannot answer this based on the provided documents."
rows = []
for l in open(sys.argv[1], encoding="utf-8"):
    if l.strip():
        r = json.loads(l); old = saved[r["Eval_ID"]]; new = r["Response"]
        rows.append({"Eval_ID": r["Eval_ID"], "identical": new == old, "sim": round(difflib.SequenceMatcher(None, new, old).ratio(), 3),
                     "new_refusal": new.startswith(REFUSAL), "saved_refusal": old.startswith(REFUSAL), "latency_s": r["latency_s"]})
out = {"n": len(rows), "identical": sum(r["identical"] for r in rows), "mean_sim": round(sum(r["sim"] for r in rows) / len(rows), 3),
       "refusal_start_matches_saved": sum(r["new_refusal"] == r["saved_refusal"] for r in rows),
       "answerable_answered": sum(not r["new_refusal"] for r in rows if not r["Eval_ID"].startswith("UNANS")),
       "unans_refused": sum(r["new_refusal"] for r in rows if r["Eval_ID"].startswith("UNANS")),
       "different": [r["Eval_ID"] for r in rows if not r["identical"]], "rows": rows}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in out.items() if k != "rows"})
