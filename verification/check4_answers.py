"""Check 4: run the 24 evaluation questions through the app's answer_question and compare with the saved STRICT_V2 responses.
Run: python check4_answers.py <eval_question_set.csv> <eval_responses.jsonl>   (needs GROQ_API_KEY in the environment; never printed)
Writes check4_responses.jsonl and check4_results.json next to this script. Resumes if interrupted."""
import sys, json, re, difflib
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import app

questions = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
saved = {}
for line in open(sys.argv[2], encoding="utf-8"):
    if line.strip():
        r = json.loads(line)
        if r["Prompt_ID"] == "STRICT_V2":
            saved[r["Eval_ID"]] = r["Response"]
assert len(saved) == 24

out_file = HERE / "check4_responses.jsonl"
done = {}
if out_file.exists():
    for line in out_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            done[r["Eval_ID"]] = r
for q in questions.itertuples():
    if q.Eval_ID in done:
        continue
    r = app.answer_question(q.Question, max_wait=None)
    rec = {"Eval_ID": q.Eval_ID, "Response": r["answer"], "ids": [i["id"] for i in r["items"]], "generation_s": round(r["generation_s"], 2),
           "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"]}
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    done[q.Eval_ID] = rec
    print(q.Eval_ID, rec["generation_s"], "s", flush=True)

# notebook's own refusal detector (cell 22), used for "answered / refused" classification
REFUSAL_RE = re.compile(r"cannot answer|can't answer|can not answer|do(es)? not (provide|contain|state|specify|mention|cover|include)|not (provided|stated|specified|mentioned|found|covered)|"
                        r"no (information|mention|provision)|walang nakasaad|hindi nakasaad|hindi (po )?(ko )?(masasagot|nabanggit|binanggit)|walang binanggit|hindi sapat|"
                        r"hindi (po )?(naglalaman|nagbibigay|saklaw|sakop|tinukoy|binabanggit|nakalagay|makikita)|walang (impormasyon|nakalagay|sinasabi|tinutukoy|detalye)|hindi (ko )?(alam|masabi)|"
                        r"insufficient|not enough information|left blank|is blank|blank|placeholder|incomplete", re.I)
TAGALOG = set("ang ng sa mga ay na po ba para kung hindi may at ito yan kailangan bayad magkano ilang ano walang nakasaad dapat siya kapag ka mo ko namin nila lang din rin pa yung sila".split())


def taglish_words(text):
    text = text.replace(app.REFUSAL_SENTENCE, " ")
    return sum(w in TAGALOG for w in re.findall(r"[a-zñ]+", text.lower()))


rows = []
for q in questions.itertuples():
    new, old = done[q.Eval_ID]["Response"], saved[q.Eval_ID]
    unans = q.Type == "Unanswerable"
    row = {"Eval_ID": q.Eval_ID, "Type": q.Type, "Question_language": q.Language,
           "new_starts_with_refusal": new.startswith(app.REFUSAL_SENTENCE), "saved_starts_with_refusal": old.startswith(app.REFUSAL_SENTENCE),
           "new_refusal_flag": bool(REFUSAL_RE.search(new)), "saved_refusal_flag": bool(REFUSAL_RE.search(old)),
           "new_tagalog_words": taglish_words(new), "saved_tagalog_words": taglish_words(old),
           "text_similarity": round(difflib.SequenceMatcher(None, new, old).ratio(), 3), "identical": new == old,
           "new_chars": len(new), "saved_chars": len(old)}
    lang_ok = (row["new_tagalog_words"] >= 3) if q.Language == "Taglish" else (row["new_tagalog_words"] <= 2)
    row["language_ok"] = lang_ok
    row["behaviour_ok"] = row["new_refusal_flag"] if unans else not row["new_starts_with_refusal"]
    row["behaviour_matches_saved"] = (row["new_starts_with_refusal"] == row["saved_starts_with_refusal"])
    rows.append(row)
df = pd.DataFrame(rows)
summary = {"questions": len(df), "identical_to_saved": int(df.identical.sum()), "mean_similarity": round(float(df.text_similarity.mean()), 3),
           "language_ok": int(df.language_ok.sum()), "answerable_answered": int(((df.Type == "Answerable") & ~df.new_starts_with_refusal).sum()),
           "unanswerable_refused_or_flagged": int(((df.Type == "Unanswerable") & df.new_refusal_flag).sum()),
           "unanswerable_start_with_refusal_sentence": int(((df.Type == "Unanswerable") & df.new_starts_with_refusal).sum()),
           "refusal_start_matches_saved": int(df.behaviour_matches_saved.sum()), "rows": rows}
(HERE / "check4_results.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print({k: v for k, v in summary.items() if k != "rows"})
print(df[["Eval_ID", "language_ok", "behaviour_ok", "behaviour_matches_saved", "text_similarity", "identical"]].to_string(index=False))
