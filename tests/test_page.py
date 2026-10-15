import os, re, sys, json, subprocess, time, tempfile, functools, http.server, threading
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def words(s): return re.findall(r"\w+", s.lower().replace("ё", "е"))
def wer(ref, hyp):
    r, h = words(ref), words(hyp); d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[:], i
        for j in range(1, len(h) + 1): d[j] = min(p[j] + 1, d[j-1] + 1, p[j-1] + (r[i-1] != h[j-1]))
    return d[-1] / max(1, len(r))
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
H.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/index.html"
res, errors, hosts = {}, [], set()
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.on("request", lambda r: hosts.add(r.url.split("/")[2]))
    pg.goto(url); pg.wait_for_timeout(1500)
    res["load_errors"] = list(errors)
    # v2: page example is FLEURS 06 (CC-BY 4.0) with ЛИРА's caption; model switcher defaults to base
    res["caption_ok"] = "FLEURS (Google), CC-BY 4.0" in pg.inner_text("[data-t=samplecap]")
    res["model_default"] = pg.evaluate("v2t.curModel()")  # v2.1: default is whisper-small (team decision 15.10)
    res["firsthint_visible"] = pg.is_visible("#firsthint")
    s = pg.evaluate("v2t.runUrl('samples/near-silent.wav')")
    res["near_silent"] = s
    t0 = time.time()
    try:
        r = pg.evaluate("v2t.runUrl('samples/sample-ru.wav')")
        hyp = " ".join(r["paragraphs"]); ref = open(f"{ROOT}/samples/sample-ru.txt").read()
        res.update(hyp=hyp, ref=ref.strip(), wer=round(wer(ref, hyp), 3), seconds=round(time.time() - t0, 1))
        res["feedback_visible"] = pg.is_visible("#feedback")
    except Exception as e: res["model_error"] = str(e)[:400]
    # v2.1: simulated hang. Tiny test-only timeout -> ЛИРА's §9 message + button; button re-runs SAME audio with base.
    pg2 = b.new_page(); pg2.goto(url + "?_test_timeout_ms=1"); pg2.wait_for_timeout(500)
    h = pg2.evaluate("v2t.runUrl('eval/06.wav')")
    st = pg2.inner_text("#status")
    res["hang"] = {"timeout": h.get("timeout"), "msg_ok": st.startswith("Точная модель думает слишком долго"), "button_visible": pg2.is_visible("#fastbtn")}
    # lift the test timeout in place (a reload would lose the kept audio)
    pg2.evaluate("v2t.setTestTimeout(0)")
    with pg2.expect_response(lambda r: "whisper-base" in r.url, timeout=120000): pg2.click("#fastbtn")
    pg2.wait_for_function("document.querySelector('#result').innerText.length > 0", timeout=180000)
    res["hang"].update(fast_text=pg2.inner_text("#result"), fast_model=pg2.evaluate("v2t.curModel()"))
    res["hang"]["fast_wer"] = round(wer("Во всех научных вопросах, включая психологию, были приняты взгляды Аристотеля.", res["hang"]["fast_text"]), 3)
    res["errors_total"] = errors; res["hosts"] = sorted(hosts)
    b.close()
print(json.dumps(res, ensure_ascii=False, indent=1))
ok = res["caption_ok"] and res["model_default"] == "Xenova/whisper-small" and res["firsthint_visible"] and res["hang"]["timeout"] and res["hang"]["msg_ok"] and res["hang"]["button_visible"] and res["hang"]["fast_model"] == "Xenova/whisper-base" and res["hang"]["fast_wer"] < 0.5 and not res["load_errors"] and res["near_silent"]["skipped"] and not res["near_silent"]["paragraphs"]
sys.exit(0 if ok else 1)
