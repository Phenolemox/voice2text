# v2.2/v2.3 microphone UX checks. Needs eval/06.wav, eval/silence.wav, eval/hyp_small_v2.csv, TEXTS_LIRA.md.
# (К1, К2, К3, К4). Fake devices only: real mics/phones are NOT covered.
import os, sys, json, csv, functools, http.server, threading
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT); H.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/index.html"
TX = {}
for line in open(f"{ROOT}/TEXTS_LIRA.md", encoding="utf-8"):  # verbatim §10 ru texts
    if "«" in line and "ru:" in line: TX.setdefault("ru", []).append(line.split("«", 1)[1].rsplit("»", 1)[0])
DENIED = next(t for t in TX["ru"] if t.startswith("Браузер не дал доступ"))
NONE = next(t for t in TX["ru"] if t.startswith("Не вижу микрофона"))
SILENT = next(t for t in TX["ru"] if t.startswith("Ничего не слышно"))
ALLOWED = {"127.0.0.1:%d" % srv.server_port, "cdn.jsdelivr.net", "huggingface.co", "us.aws.cdn.hf.co"}
res, hosts = {}, set()
def reject(name): return f"navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('x', '{name}'));"
def page(b, init=None, perms=None):
    ctx = b.new_context(permissions=perms or []); pg = ctx.new_page()
    pg.on("request", lambda r: hosts.add(r.url.split("/")[2]))
    if init: pg.add_init_script(init)
    pg.goto(url); pg.wait_for_timeout(500); return pg
def sample_meter(pg, secs):
    vals = []
    for _ in range(secs * 10): pg.wait_for_timeout(100); vals.append(float(pg.evaluate("document.getElementById('vbar').dataset.rms || 0")))
    return vals
def var(v): m = sum(v) / len(v); return sum((x - m) ** 2 for x in v) / len(v)
with sync_playwright() as p:
    base = ["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
    # К2a denied, REAL browser denial (adopted from АРГУС journal/argus-accept3/argus_v22.py):
    # fake device present, NO --use-fake-ui-for-media-stream, context without microphone grant -> Chrome itself rejects.
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-fake-device-for-media-stream"])
    pg = page(b); res["denied_real_gum"] = pg.evaluate("navigator.mediaDevices.getUserMedia({audio:true}).then(s=>{s.getTracks().forEach(t=>t.stop());return 'OK'},e=>e.name)")
    pg = page(b); pg.click("#rec"); pg.wait_for_timeout(1500)
    res["denied"] = res["denied_real_gum"] == "NotAllowedError" and pg.inner_text("#micmsg") == DENIED
    pg.click("#lang"); res["denied_en"] = pg.inner_text("#micmsg").startswith("The browser blocked the microphone.")
    b.close()
    # К2b' no device, REAL: no fake device, fake-ui accepts, granted -> Chrome reports NotFoundError
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--use-fake-ui-for-media-stream"])
    pg = page(b, perms=["microphone"]); pg.click("#rec"); pg.wait_for_timeout(1500)
    res["nodevice_real"] = pg.inner_text("#micmsg") == NONE
    b.close()
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--autoplay-policy=no-user-gesture-required"])
    # К2b no device (SIMULATED via init script)
    pg = page(b, reject("NotFoundError")); pg.click("#rec"); pg.wait_for_timeout(500)
    res["nodevice_sim"] = pg.inner_text("#micmsg") == NONE
    pg = page(b, reject("OverconstrainedError")); pg.click("#rec"); pg.wait_for_timeout(500)
    res["overconstrained_sim"] = pg.inner_text("#micmsg") == NONE
    # К4 recognition of 06 byte-identical to eval/hyp_small_v2.csv
    ref = {r["file"]: r["hypothesis"] for r in csv.DictReader(open(f"{ROOT}/eval/hyp_small_v2.csv", encoding="utf-8"))}["06.wav"]
    r = pg.evaluate("v2t.runUrl('eval/06.wav')"); res["k4_hyp"] = " ".join(r["paragraphs"]); res["k4"] = res["k4_hyp"] == ref
    b.close()
    # К1 + К2c silence
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=base + [f"--use-file-for-fake-audio-capture={ROOT}/eval/silence.wav"])
    pg = page(b, perms=["microphone"]); pg.click("#rec"); vs = sample_meter(pg, 4)
    res["silence"] = {"max_rms": max(vs), "msg": pg.is_visible("#micmsg") and pg.inner_text("#micmsg") == SILENT}
    pg.click("#stop"); pg.wait_for_timeout(500); res["silence"]["meter_hidden_after_stop"] = not pg.is_visible("#meter")
    b.close()
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=base + [f"--use-file-for-fake-audio-capture={ROOT}/eval/06.wav"])
    pg = page(b, perms=["microphone"]); pg.click("#rec"); vs = sample_meter(pg, 3)
    res["speech"] = {"var": var(vs), "max_rms": max(vs), "widths": len(set(vs)), "silent_msg": pg.is_visible("#micmsg")}
    pg.click("#stop"); b.close()
res["hosts"] = sorted(hosts); res["hosts_ok"] = hosts <= ALLOWED
print(json.dumps(res, ensure_ascii=False, indent=1))
ok = (res["denied"] and res["nodevice_real"] and res["denied_en"] and res["nodevice_sim"] and res["overconstrained_sim"] and res["k4"] and res["silence"]["msg"]
      and res["silence"]["max_rms"] < 0.003 and res["silence"]["meter_hidden_after_stop"] and res["speech"]["var"] > 0 and not res["speech"]["silent_msg"] and res["hosts_ok"])
sys.exit(0 if ok else 1)
