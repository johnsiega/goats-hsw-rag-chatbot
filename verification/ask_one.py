import sys, time
from gradio_client import Client
t = time.perf_counter()
c = Client(sys.argv[1], verbose=False)
h, _ = c.predict("How many rest days per week does the standard contract give the worker?", [], api_name="/ask")
x = h[-1]["content"]
if isinstance(x, list): x = "".join(b.get("text", "") for b in x if isinstance(b, dict))
print(f"{time.perf_counter()-t:.1f}s  busy={'busy' in x[:60]}  has_sources={'**Sources**' in x or 'Sources' in x}  len={len(x)}")
