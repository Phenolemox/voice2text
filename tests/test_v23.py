# v2.3 checks: К0 (shared preload), К1 (feedback link), К2 (copy, both paths), К3 (ЛИРА: speak while loading), К4 hosts.
# Clean cache = fresh persistent profile per run; slow network = CDP throttling (no new hosts, nothing routed).
import os, sys, json, re, time, tempfile, functools, http.server, threading
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT); H.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}/index.html"
TX = open(f"{ROOT}/TEXTS_LIRA.md", encoding="utf-8").read()
def sec(n): return TX.split(f"## {n}.")[1].split("\n## ")[0]
Q1, Q2 = re.findall(r"ru: «(.+?)»", sec(5))[:2]
s11 = sec(11); COPIED = re.search(r"Успех.*?«(.+?)»", s11).group(1); FAIL = re.search(r"Ошибка.*?«(.+?)»", s11).group(1)
Q3 = re.search(r"Вопрос в отзыве: «(.+?)»", s11).group(1); OPTS = re.findall(r"^- «(.+?)»", s11, re.M)
s12 = sec(12); CANSPEAK, SAVED = re.findall(r"«(.+?)»", s12)[:2]
CH = "/usr/bin/google-chrome"; REQ = []; R = {}
def ctx(p, args=(), perms=(), throttle=None):
    c = p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=CH, args=list(args), permissions=list(perms))
    pg = c.pages[0]; pg.on("request", lambda r: r.url.startswith("http") and REQ.append((r.method, urlparse(r.url).netloc, len(r.post_data_buffer or b""))))
    if throttle:
        s = c.new_cdp_session(pg); s.send("Network.enable")
        s.send("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": throttle, "uploadThroughput": -1})
    return c, pg
WORDS06 = set(re.findall(r"\w+", "Во всех научных вопросах, включая психологию, были приняты взгляды арестотеля".lower()))
with sync_playwright() as p:
    # ---- К0: concurrent preloads (same model twice + model switch during download) all resolve ----
    c, pg = ctx(p, throttle=15e6); pg.goto(URL + "?model=base")
    pg.evaluate("window._k0 = Promise.all([v2t.preload(), v2t.preload(), v2t.preload('Xenova/whisper-small')]).then(() => 'ok'); 0")
    pg.wait_for_function("window._k0 && v2t.isReady('Xenova/whisper-base') && v2t.isReady('Xenova/whisper-small')", timeout=240000)
    R["k0_concurrent"] = pg.evaluate("window._k0"); c.close()
    # ---- К3 (+К0 record+sample): clean cache, slow network, record before model is ready ----
    c, pg = ctx(p, args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-audio-capture={ROOT}/eval/06.wav"],
                perms=["microphone"], throttle=8e6)
    pg.goto(URL); pg.wait_for_timeout(500); t0 = time.time()
    pg.click("#rec"); pcts = []
    for _ in range(8):
        pg.wait_for_timeout(500)
        if pg.is_visible("#canspeak"):
            t = pg.inner_text("#canspeak"); m = re.search(r"\((\d+)%\)", t)
            if m and t == CANSPEAK.replace("N", m.group(1)): pcts.append(int(m.group(1)))
    pg.evaluate("window._sample = v2t.runUrl('eval/06.wav').then(r => r.paragraphs.join(' ')); 0")  # second concurrent preload (К0)
    pg.evaluate("window._rec = v2t.stopRec(); 0"); pg.wait_for_timeout(1500)
    st = pg.inner_text("#status"); ms = re.match(re.escape(SAVED).replace("N", r"(\d+)") + "$", st)
    R["k3"] = {"pcts": pcts, "grows": len(pcts) >= 2 and pcts[-1] > pcts[0], "ready_at_stop": pg.evaluate("v2t.isReady()"),
               "saved_caption": bool(ms), "status": st, "rec_blocked_while_waiting": pg.is_disabled("#rec")}
    pg.wait_for_function("document.querySelector('#result').innerText.length > 0", timeout=300000)
    pg.evaluate("window._recdone = window._rec.then(() => 1); 0")
    pg.wait_for_function("window._recdone && v2t.isReady()", timeout=300000); pg.wait_for_timeout(500)
    rec_text = pg.evaluate("window._rec.then(r => r ? r.paragraphs.join(' ') : '')")
    R["k3"].update(rec_text=rec_text, sample_text=pg.evaluate("window._sample"), seconds=round(time.time() - t0, 1),
                   rec_unblocked=not pg.is_disabled("#rec"), canspeak_hidden=not pg.is_visible("#canspeak"))
    R["k3"]["rec_has_06_words"] = len(WORDS06 & set(re.findall(r"\w+", rec_text.lower()))) >= 3
    R["k3"]["sample_06_words"] = len(WORDS06 & set(re.findall(r"\w+", R["k3"]["sample_text"].lower()))) >= 6
    c.close()
    # ---- К1 + К2: result of 06, feedback link, copy ok / copy rejected ----
    c, pg = ctx(p, perms=["clipboard-read", "clipboard-write"]); pg.goto(URL)
    r = pg.evaluate("v2t.runUrl('eval/06.wav')"); transcript = " ".join(r["paragraphs"])
    gh_before = [x for x in REQ if "github" in x[1]]
    href = pg.get_attribute("#fblink", "href"); u = urlparse(href); q = parse_qs(u.query); body = q.get("body", [""])[0]
    tw = set(re.findall(r"\w+", transcript.lower())) - set(re.findall(r"\w+", (Q1 + Q2 + Q3 + " ".join(OPTS)).lower()))
    R["k1"] = {"github_requests_before_click": len(gh_before), "prefix_ok": href.startswith("https://github.com/Phenolemox/workshop-notes/issues/new"),
               "q_ok": all(x in body for x in [Q1, Q2, Q3] + OPTS), "model_ok": "Модель: Точная" in body, "switch_ok": "Переходил на „Быструю“: нет" in body,
               "no_transcript": not any(re.search(r"\b" + re.escape(w) + r"\b", body.lower()) for w in tw if len(w) > 3), "url_len": len(href), "body": body}
    pg.click("#lang"); en_body = parse_qs(urlparse(pg.get_attribute("#fblink", "href")).query)["body"][0]; pg.click("#lang")
    R["k1"]["en_ok"] = "What did you do with the text?" in en_body
    pg.click("#copybtn"); pg.wait_for_selector("#copymsg:not([hidden])")
    R["k2_ok"] = {"caption": pg.inner_text("#copymsg") == COPIED, "clipboard_equal": pg.evaluate("navigator.clipboard.readText()") == transcript}
    pg.wait_for_timeout(2300); R["k2_ok"]["hidden_after_2s"] = not pg.is_visible("#copymsg")
    # rejected writeText: caption must NOT be the success one; text selected; §11 error shown
    pg.evaluate("navigator.clipboard.writeText = () => Promise.reject(new DOMException('denied', 'NotAllowedError')); 0")
    pg.evaluate("getSelection().removeAllRanges(); 0"); pg.click("#copybtn"); pg.wait_for_timeout(300)
    R["k2_fail"] = {"error_text": pg.inner_text("#copymsg") == FAIL, "selected": pg.evaluate("getSelection().toString().trim()") == pg.inner_text("#result").strip()}
    # absent API
    pg.evaluate("Object.defineProperty(navigator, 'clipboard', {value: undefined}); getSelection().removeAllRanges(); 0"); pg.click("#copybtn"); pg.wait_for_timeout(300)
    R["k2_noapi"] = {"error_text": pg.inner_text("#copymsg") == FAIL, "selected": len(pg.evaluate("getSelection().toString()")) > 10}
    c.close()
    # rejected clipboard via init script from the start (fresh page), no success caption ever shown
    c, pg = ctx(p); pg.add_init_script("navigator.clipboard.writeText = () => Promise.reject(new DOMException('denied', 'NotAllowedError'))")
    pg.goto(URL); seen = []
    pg.evaluate("new MutationObserver(() => { const m = document.getElementById('copymsg'); if (!m.hidden) (window._seen = window._seen || []).push(m.textContent); }).observe(document.getElementById('copymsg'), {attributes: true, childList: true, characterData: true, subtree: true}); 0")
    pg.evaluate("v2t.runUrl('eval/06.wav')"); pg.click("#copybtn"); pg.wait_for_timeout(500)
    R["k2_init"] = {"seen": pg.evaluate("window._seen || []"), "no_success": COPIED not in pg.evaluate("window._seen || []"), "error_text": pg.inner_text("#copymsg") == FAIL}
    c.close()
hosts = sorted({h for _, h, _ in REQ})
R["k4"] = {"hosts": hosts, "methods": sorted({m for m, _, _ in REQ}), "with_body": [x for x in REQ if x[2] > 0],
           "hosts_ok": all(h.startswith("127.0.0.1") or h in ("cdn.jsdelivr.net", "huggingface.co") or h.endswith(".cdn.hf.co") for h in hosts)}
print(json.dumps(R, ensure_ascii=False, indent=1))
k1 = R["k1"]; k3 = R["k3"]
ok = (R["k0_concurrent"] == "ok" and k1["github_requests_before_click"] == 0 and k1["prefix_ok"] and k1["q_ok"] and k1["model_ok"] and k1["switch_ok"]
      and k1["no_transcript"] and k1["url_len"] < 8000 and k1["en_ok"] and all(R["k2_ok"].values()) and all(R["k2_fail"].values()) and all(R["k2_noapi"].values())
      and R["k2_init"]["no_success"] and R["k2_init"]["error_text"] and k3["grows"] and not k3["ready_at_stop"] and k3["saved_caption"] and k3["rec_blocked_while_waiting"]
      and k3["rec_has_06_words"] and k3["sample_06_words"] and k3["rec_unblocked"] and k3["canspeak_hidden"]
      and R["k4"]["hosts_ok"] and R["k4"]["methods"] == ["GET"] and not R["k4"]["with_body"])
sys.exit(0 if ok else 1)
