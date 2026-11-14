"""Browser checks for the v4 UI with Playwright (Chromium).
usage: python ui_test.py local  <base_url>     (stub server: screenshots + layout/contrast/focus/Enter checks)
       python ui_test.py remote <base_url> <prefix>   (real service: wait for the page, ask one question at 390 px, screenshot)
Needs no model and no secret. Output: ui_v4_*.png next to this file and a JSON summary on stdout."""
import sys, json, time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
MODE, BASE = sys.argv[1], sys.argv[2].rstrip("/")
Q = "How many hours of continuous daily rest and how many rest days per week does the standard contract give the worker?"

CONTRAST_JS = r"""() => {
  const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d', {willReadFrequently: true});
  const rgba = c => { cx.clearRect(0,0,1,1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.fillRect(0,0,1,1); const d = cx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2],d[3]/255]; };
  const lum = ([r,g,b]) => { const f = v => { v/=255; return v<=.03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }; return .2126*f(r)+.7152*f(g)+.0722*f(b); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor); if (c[3] > .97) return c; } return rgba(getComputedStyle(document.body).backgroundColor); };
  const sels = {
    'bot message': '#chat .message.bot .prose p', 'user message': '#chat .message.user .prose p', 'passage text': '#chat details.sheet li',
    'passage heading': '#chat details.sheet li b', 'sheet summary': '#chat details.sheet summary', 'source chip': '#chat code',
    'notice': '.notice p', 'lead text': '.lead p', 'header title': '.hdr h1', 'header subtitle': '.hdr p', 'Ask button': '#send',
    'example chip': '.chip', 'input text': '#q textarea', 'About label': '.about .label-wrap', 'chips label': '.chips-label p'};
  const out = {};
  for (const [name, s] of Object.entries(sels)) {
    const el = document.querySelector(s); if (!el) { out[name] = null; continue; }
    const fg = rgba(getComputedStyle(el).color), bg = bgOf(el);
    const a = lum(fg), b = lum(bg); out[name] = +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
  }
  return out; }"""

SMALL_JS = r"""() => [...document.querySelectorAll('button, summary, textarea, a, .label-wrap')].filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && (r.height < 43.5 || r.width < 43.5); })
  .map(e => (e.id || e.className || e.tagName).toString().slice(0, 40) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


def ask(pg, text, expect_answer=True):
    pg.fill("#q textarea", text)
    pg.keyboard.press("Enter")
    if expect_answer:
        pg.wait_for_selector("#chat details.sheet", timeout=120000)
    pg.wait_for_timeout(500)


def local():
    res = {"external_requests": [], "small_targets": {}}
    host = urlparse(BASE).netloc
    with sync_playwright() as p:
        b = p.chromium.launch()

        def page(w, h, scheme="light", theme=None):
            ctx = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, device_scale_factor=2 if w < 600 else 1, has_touch=w < 600, is_mobile=w < 600)
            pg = ctx.new_page()
            pg.on("request", lambda r: res.setdefault("font_requests", []).append(r.url) if r.url.split("?")[0].endswith((".woff", ".woff2", ".ttf")) else None)
            pg.on("request", lambda r: res["external_requests"].append(r.url) if urlparse(r.url).netloc not in (host, "") and not r.url.startswith(("data:", "blob:")) else None)
            pg.goto(BASE + ("/?__theme=" + theme if theme else "/"))
            pg.wait_for_selector("#q textarea", timeout=30000)
            pg.wait_for_timeout(600)
            return pg

        # mobile, empty state
        pg = page(390, 844)
        res["mobile_overflow_x"] = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        res["small_targets"]["390 empty"] = pg.evaluate(SMALL_JS)
        pg.screenshot(path=str(HERE / "ui_v4_mobile.png"))
        # example chips fill the box with the full question
        import re as _re
        pg.click(".chip >> nth=1")
        pg.wait_for_function("document.querySelector('#q textarea').value.length > 0", timeout=5000)
        res["chip_fills_box"] = pg.input_value("#q textarea")
        pg.fill("#q textarea", "")
        # Enter sends, Shift+Enter adds a line
        pg.fill("#q textarea", "line one")
        pg.keyboard.press("Shift+Enter")
        pg.keyboard.type("line two")
        res["shift_enter_value"] = pg.input_value("#q textarea")
        pg.fill("#q textarea", "")
        # waiting state (first question: "waking up" text), stub takes STUB_DELAY seconds
        pg.fill("#q textarea", Q)
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#chat .wait", timeout=10000)
        pg.wait_for_timeout(700)
        res["wait_text"] = pg.inner_text("#chat .wait")
        res["dots"] = pg.evaluate("document.querySelectorAll('#chat .dots i').length")
        pg.screenshot(path=str(HERE / "ui_v4_loading.png"))
        pg.wait_for_selector("#chat details.sheet", timeout=60000)
        pg.wait_for_timeout(600)
        res["box_after_enter"] = pg.input_value("#q textarea")
        res["small_targets"]["390 answer"] = pg.evaluate(SMALL_JS)
        res["contrast_light_390"] = pg.evaluate(CONTRAST_JS)
        pg.screenshot(path=str(HERE / "ui_v4_light.png"))
        pg.click("#chat details.sheet summary")
        pg.wait_for_timeout(600)
        res["contrast_light_390_open"] = pg.evaluate(CONTRAST_JS)
        pg.screenshot(path=str(HERE / "ui_v4_answer_sources.png"))
        # keyboard focus
        pg.click("#q textarea")
        seen = []
        for _ in range(6):
            pg.keyboard.press("Tab")
            seen.append(pg.evaluate("(()=>{const e=document.activeElement,s=getComputedStyle(e);return (e.id||e.className||e.tagName).toString().slice(0,24)+' outline='+s.outlineWidth+' '+s.outlineStyle})()"))
        res["focus_after_tab"] = seen
        pg.context.close()

        # dark (Gradio follows the system scheme; also check the explicit ?__theme=dark)
        pg = page(390, 844, scheme="dark")
        res["dark_body_class_from_system"] = pg.evaluate("document.body.className")
        ask(pg, Q)
        res["contrast_dark_390"] = pg.evaluate(CONTRAST_JS)
        pg.click("#chat details.sheet summary")
        pg.wait_for_timeout(500)
        res["contrast_dark_390_open"] = pg.evaluate(CONTRAST_JS)
        res["small_targets"]["390 dark"] = pg.evaluate(SMALL_JS)
        pg.screenshot(path=str(HERE / "ui_v4_dark.png"))
        pg.context.close()
        # desktop
        pg = page(1280, 900)
        ask(pg, Q)
        res["small_targets"]["1280"] = pg.evaluate(SMALL_JS)
        res["contrast_light_1280"] = pg.evaluate(CONTRAST_JS)
        pg.screenshot(path=str(HERE / "ui_v4_desktop.png"))
        pg.context.close()
        b.close()
    print(json.dumps(res, indent=1))


def remote():
    prefix = sys.argv[3] if len(sys.argv) > 3 else "ui_v4_remote"
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        host = urlparse(BASE).netloc
        res["external_requests"] = []
        pg.on("request", lambda r: res["external_requests"].append(r.url) if urlparse(r.url).netloc not in (host, "") and not r.url.startswith(("data:", "blob:")) else None)
        t = time.time()
        pg.goto(BASE + "/", timeout=240000)
        pg.wait_for_selector("#q textarea", timeout=240000)
        res["page_ready_s"] = round(time.time() - t, 1)
        res["overflow_x"] = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(HERE / f"{prefix}_390_loaded.png"))
        t = time.time()
        pg.fill("#q textarea", Q)
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#chat .wait", timeout=15000)
        res["wait_text"] = pg.inner_text("#chat .wait")
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(HERE / f"{prefix}_390_waiting.png"))
        pg.wait_for_selector("#chat details.sheet", timeout=120000)
        res["first_answer_s"] = round(time.time() - t, 1)
        pg.wait_for_timeout(600)
        res["sources_marker"] = "Sources" in pg.inner_text("#chat")
        res["passage_items"] = pg.evaluate("document.querySelectorAll('#chat details.sheet li').length")
        pg.click("#chat details.sheet summary")
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(HERE / f"{prefix}_390_answer_sources.png"))
        b.close()
    print(json.dumps(res, indent=1))


local() if MODE == "local" else remote()
