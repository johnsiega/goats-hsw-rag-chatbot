"""Checks 2, 3, 4 (generation part) and 5 against the deployed Cloud Run service through gradio_client.
Run: python remote_checks.py <service_url> <eval_question_set.csv> [parts: 23 4 5]
The embedding model runs inside the service; nothing is embedded on this PC. No secrets are used or printed."""
import sys, json, time, random
from pathlib import Path

import pandas as pd
from gradio_client import Client

HERE = Path(__file__).parent
URL, QCSV = sys.argv[1], sys.argv[2]
parts = sys.argv[3] if len(sys.argv) > 3 else "2345"
LOGS = r"D:\Final Project\Next Run v2\Goats_Experiment_Logs.xlsx"
BUSY = "The assistant is busy"
questions = pd.read_csv(QCSV, encoding="utf-8-sig")
chunks = [json.loads(l) for l in (HERE.parent / "data" / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
client = Client(URL, verbose=False)
res_file = HERE / "remote_results.json"
res = json.loads(res_file.read_text(encoding="utf-8")) if res_file.exists() else {}


def save():
    res_file.write_text(json.dumps(res, indent=1), encoding="utf-8")


def retrieve_ids(text):
    t = time.perf_counter()
    out = json.loads(client.predict(text, api_name="/retrieve_ids"))
    return out, time.perf_counter() - t


def ask(text):
    t = time.perf_counter()
    hist, _ = client.predict(text, [], api_name="/ask")
    content = hist[-1]["content"]
    if isinstance(content, list):                          # gradio 6 returns content blocks
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content, time.perf_counter() - t


if "2" in parts or "3" in parts:
    # first call = cold start if no instance is warm
    _, cold_s = retrieve_ids("What is the capital city of Australia?")
    _, warm_s = retrieve_ids("What is the capital city of Australia?")
    res["latency_retrieval_only"] = {"first_call_s": round(cold_s, 2), "second_call_s": round(warm_s, 2)}
    print("retrieval latency first/second", cold_s, warm_s, flush=True)

if "2" in parts:
    # chunks of at most 500 characters (the endpoint truncates longer text), 20 random ones (seed 7)
    random.seed(7)
    pool = [c["Chunk_ID"] for c in chunks if len(c["Text"]) <= 500]
    ids = random.sample(pool, 20)
    rows, cos_list = [], []
    for cid in ids:
        top, _ = retrieve_ids(chunks[cid]["Text"])
        d = top[0][1]
        own = {c["Chunk_ID"] for c in chunks if c["Text"] == chunks[cid]["Text"]}
        cos = 1 - d / 2                      # unit vectors: squared L2 = 2 - 2 cos
        cos_list.append(cos)
        rows.append({"chunk": cid, "top1": top[0][0], "top1_is_own_text": top[0][0] in own, "sq_l2": d, "cosine": round(cos, 6)})
    res["check2"] = {"n": 20, "pool_size_le_500_chars": len(pool), "min_cosine": min(cos_list), "all_top1_own": all(r["top1_is_own_text"] for r in rows), "rows": rows}
    print("check2 min cosine", min(cos_list), "own top1:", res["check2"]["all_top1_own"], flush=True)
    save()

if "3" in parts:
    ref = pd.read_excel(LOGS, sheet_name="06_Retrieval")
    rows, match, dmax = [], 0, 0.0
    for q in questions.itertuples():
        top, _ = retrieve_ids(q.Question)
        got = [t[0] for t in top]
        r = ref[ref.Eval_ID == q.Eval_ID].sort_values("Rank")
        want = [int(x) for x in r.Chunk_ID]
        ok = got == want
        dd = max(abs(a[1] - b) for a, b in zip(top, r.Distance)) if ok else None
        if dd is not None:
            dmax = max(dmax, dd)
        match += ok
        rows.append({"Eval_ID": q.Eval_ID, "match": ok, "service_top5": got, "log_top5": want, "same_set": sorted(got) == sorted(want), "max_abs_dist_diff": dd})
    res["check3"] = {"questions": len(rows), "exact_matches": match, "max_abs_distance_diff_on_matches": dmax, "rows": rows}
    print("check3", match, "/", len(rows), "max dist diff", dmax, flush=True)
    for r in rows:
        if not r["match"]:
            print("MISMATCH", r, flush=True)
    save()

if "4" in parts:
    out_file = HERE / "check4_responses.jsonl"
    done = {}
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done[json.loads(line)["Eval_ID"]] = 1
    lat = []
    for q in questions.itertuples():
        if q.Eval_ID in done:
            continue
        for attempt in range(8):
            time.sleep(5)                                  # per-session cooldown is 4 s
            reply, secs = ask(q.Question)
            if reply.startswith(BUSY) or reply.startswith("Please wait"):
                time.sleep(35)                             # let the Groq token pacer window recover
                continue
            break
        answer = reply.split("\n\n**Sources**")[0]
        rec = {"Eval_ID": q.Eval_ID, "Response": answer, "has_sources_block": "**Sources**" in reply,
               "has_passages_block": "Retrieved passages" in reply, "latency_s": round(secs, 2), "attempts": attempt + 1}
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        lat.append(secs)
        print(q.Eval_ID, round(secs, 1), "s", "attempts", attempt + 1, flush=True)
    res["check4_generation_latency_s"] = {"n": len(lat), "mean": round(sum(lat) / len(lat), 2) if lat else None, "max": round(max(lat), 2) if lat else None}
    save()

if "5" in parts:
    smoke = {}
    time.sleep(5)
    for name, text in [("english", "How many professions fall within the scope of domestic workers under the HRSD guide?"),
                       ("taglish", "Magkano ang end-of-service benefit ng domestic worker at ilang taon ng serbisyo ang kailangan?"),
                       ("unanswerable", "What is the weather like in Riyadh in July?")]:
        for _ in range(6):
            time.sleep(5)
            reply, secs = ask(text)
            if not (reply.startswith(BUSY) or reply.startswith("Please wait")):
                break
            time.sleep(35)
        smoke[name] = {"latency_s": round(secs, 2), "first_line": reply.split("\n")[0][:200], "has_sources": "**Sources**" in reply,
                       "has_passages": "Retrieved passages" in reply, "passage_items": reply.count("<li>")}
    time.sleep(5)
    smoke["empty_input"] = ask("   ")[0]
    time.sleep(5)
    long_q = ("What are the rights of a domestic worker? " * 20)[:600]
    smoke["input_600_chars"] = {"len": len(long_q), "reply": ask(long_q)[0][:200]}
    res["check5"] = smoke
    print(json.dumps(smoke, indent=1, ensure_ascii=False), flush=True)
    save()
