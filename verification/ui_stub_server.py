"""Local UI test server: imports the real app.py UI but stubs retrieval and Groq, so bge-m3 is never loaded.
usage: python ui_stub_server.py <port> ; env STUB_DELAY (seconds the stub 'model' takes, default 3)"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app, uvicorn

DELAY = float(os.environ.get("STUB_DELAY", "3"))
app.retrieve = lambda q, n=5: [{"rank": i + 1, "id": str(i), "text": app.CHUNKS[i * 40]["Text"], "source": app.CHUNKS[i * 40]["Source"] or "Unknown",
                                "page": app.CHUNKS[i * 40]["page"], "start": 0, "distance": 0.1 * i} for i in range(n)]
def fake_groq(messages, max_wait=8):
    time.sleep(DELAY)
    return {"text": "Domestic workers are entitled to at least **9 hours** of continuous daily rest and one rest day per week "
                    "[Standard_Employment_Contract_HSW_SaudiArabia.txt].\n\nIf you counted the items in the list, say so; the documents do not state more.",
            "prompt_tokens": 1, "completion_tokens": 1, "seconds": DELAY}
app.call_groq = fake_groq
uvicorn.run(app.make_app(), host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
