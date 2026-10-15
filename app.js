"use strict";
// ---- texts (verbatim from TEXTS_LIRA.md where provided) ----
const T = {
  ru: { title:"Голос в текст", privacy:"Голос не уходит с вашего устройства. Абзацы расставлены по паузам.",
    dl:"Скачиваю модель распознавания: {done} из {total} МБ. Это нужно один раз, дальше всё работает прямо на вашем устройстве.",
    sample:"Попробовать на примере", samplecap:"Пример на живом голосе: зачитанная фраза, одна из удачных. Среднее качество ниже, на вашем голосе может быть иначе. Запись: FLEURS (Google), CC-BY 4.0.",
    mfast:"Быстрая (~80 МБ, ошибается чаще)", msmall:"Точная (~250 МБ, скачивается один раз)", firsthint:"Первый запуск дольше: скачиваю модель. На мобильном интернете лучше выбрать „Быструю“.",
    fb:"Как получилось? Напишите пару слов в issue №1, нам важен каждый честный отзыв.",
    q1:"Что запомнилось?", q2:"Чем это лучше того, чем вы пользуетесь сейчас?", qcap:"Пара слов в issue №1, без готовых вариантов",
    rec:"🎙 Диктовать", stop:"■ Стоп", file:"или файл:", hint:"До ~30 секунд. Запись остановится сама после 2 секунд тишины.",
    silent:"Похоже, в записи тишина — распознавать нечего.", working:"Распознаю…", listening:"Слушаю…", lang:"EN", timeout:"Точная модель думает слишком долго, поэтому я её остановила. Попробуйте „Быструю“: она справится за секунды, хоть и ошибается чаще. Запись не потерялась.", fastbtn:"Расшифровать быстрой",
    vlabel:"Вас слышно", micdenied:"Браузер не дал доступ к микрофону. Нажмите на значок замка или микрофона слева от адреса страницы и выберите „Разрешить“, затем обновите страницу. На iPhone: Настройки → Safari → Микрофон.",
    micnone:"Не вижу микрофона. Подключите наушники с микрофоном или откройте страницу на телефоне. А пока можно попробовать на готовом примере ниже.",
    micsilent:"Ничего не слышно. Проверьте, какой микрофон выбран, и не выключен ли звук на гарнитуре." },
  en: { title:"Voice to text", privacy:"Your voice never leaves your device. Paragraphs are split by pauses.",
    dl:"Downloading the speech model: {done} of {total} MB. This happens once; after that everything runs on your device.",
    sample:"Try a sample", samplecap:"A real-voice sample: a read-aloud phrase, one of the better results. Average quality is lower and may differ for your voice. Recording: FLEURS (Google), CC-BY 4.0.",
    mfast:"Fast (~80 MB, more mistakes)", msmall:"Accurate (~250 MB, downloaded once)", firsthint:"First run takes longer while the model downloads. On mobile data, pick „Fast“.",
    fb:"How did it go? Leave a couple of words in issue #1, every honest review helps.",
    q1:"What stuck with you?", q2:"How is this better than what you use now?", qcap:"A few words in issue #1, in your own words",
    rec:"🎙 Dictate", stop:"■ Stop", file:"or a file:", hint:"Up to ~30 seconds. Recording stops by itself after 2 seconds of silence.",
    silent:"Looks like the recording is silent — nothing to transcribe.", working:"Transcribing…", listening:"Listening…", lang:"RU", timeout:"The accurate model is taking too long, so I stopped it. Try „Fast“: it finishes in seconds, though it makes more mistakes. Your recording is still here.", fastbtn:"Transcribe with Fast",
    vlabel:"I can hear you", micdenied:"The browser blocked the microphone. Tap the lock or microphone icon left of the page address, choose „Allow“, then reload. On iPhone: Settings → Safari → Microphone.",
    micnone:"No microphone found. Plug in a headset or open this page on your phone. Meanwhile, you can try the sample below.",
    micsilent:"I can't hear anything. Check which microphone is selected and that your headset isn't muted." },
};
let L = "ru";
const $ = (id) => document.getElementById(id);
function applyLang() {
  document.documentElement.lang = L;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = T[L][el.dataset.t]; });
  $("lang").textContent = T[L].lang;
  const m = $("micmsg"); if (m && m.dataset.k) m.textContent = T[L][m.dataset.k];
}
$("lang").onclick = () => { L = L === "ru" ? "en" : "ru"; applyLang(); };

// ---- settings ----
const SR = 16000, MAX_SEC = 30, SILENCE_MS = 2000;
const SPEECH_RMS = 0.02, TRIM_RMS = 0.01, SILENT_RMS = 0.005, PARA_GAP_S = 1.2, SENT_PER_PARA = 3;
// v2: quiet speech is peak-normalized (gain capped) before trimming; "is there speech" is judged by
// dynamic range of 20 ms frame energy (speech has pauses/syllables, stationary noise is flat).
const MIN_PEAK = 0.005, TARGET_PEAK = 0.9, MAX_GAIN = 30, MIN_DYN_DB = 15;
const STOPLIST = [/^[\s.,!…-]*(субтитры|subtitles)[\s.,!…-]*$/i, /субтитры (сделал|создавал|подготовил|делал)/i, /^[\s.,!…-]*(редактор|корректор)[\s.,!…-]*$/i, /продолжение следует/i, /спасибо за просмотр/i,
  /редактор субтитров/i, /корректор/i, /thank(s| you) for watching/i, /subtitles by/i, /подписывайтесь на канал/i];

// ---- audio helpers ----
function rms(a, s = 0, e = a.length) { let x = 0; for (let i = s; i < e; i++) x += a[i] * a[i]; return Math.sqrt(x / Math.max(1, e - s)); }
function peak(a) { let m = 0; for (let i = 0; i < a.length; i++) { const v = Math.abs(a[i]); if (v > m) m = v; } return m; }
function normalize(a) { const p = peak(a); const g = p > 0 ? Math.min(MAX_GAIN, TARGET_PEAK / p) : 1; const b = new Float32Array(a.length); for (let i = 0; i < a.length; i++) b[i] = a[i] * g; return { a: b, peak: p, gain: g }; }
function dynRangeDb(a) {
  const w = SR / 50, db = [];
  for (let s = 0; s + w <= a.length; s += w) db.push(20 * Math.log10(rms(a, s, s + w) + 1e-6));
  if (db.length < 5) return 0; db.sort((x, y) => x - y);
  return db[Math.floor(db.length * 0.9)] - db[Math.floor(db.length * 0.1)];
}
// Drops degenerate repetitive output (typical Whisper hallucination on noise).
function repetitive(t) { const w = (t.toLowerCase().match(/[\p{L}\p{N}]+/gu) || []); if (w.length < 12) return false; return new Set(w).size / w.length < 0.35; }
function trim(a) {
  const w = SR / 50; let s = 0, e = a.length;
  while (s + w < e && rms(a, s, s + w) < TRIM_RMS) s += w;
  while (e - w > s && rms(a, e - w, e) < TRIM_RMS) e -= w;
  return a.subarray(Math.max(0, s - w * 10), Math.min(a.length, e + w * 10)); // keep 0.2 s margins
}
async function toMono16k(buf, rate) {
  const ctx = new OfflineAudioContext(1, Math.ceil(buf.length * SR / rate), SR);
  const b = ctx.createBuffer(1, buf.length, rate); b.copyToChannel(buf, 0);
  const src = ctx.createBufferSource(); src.buffer = b; src.connect(ctx.destination); src.start();
  return (await ctx.startRendering()).getChannelData(0);
}
async function decode(arrayBuf) {
  const ac = new AudioContext(); const ab = await ac.decodeAudioData(arrayBuf); ac.close();
  const ch = ab.getChannelData(0).slice();
  if (ab.numberOfChannels > 1) { const c2 = ab.getChannelData(1); for (let i = 0; i < ch.length; i++) ch[i] = (ch[i] + c2[i]) / 2; }
  return toMono16k(ch, ab.sampleRate);
}

// ---- paragraphs ----
function clean(t) { t = (t || "").trim(); return STOPLIST.some((r) => r.test(t)) || repetitive(t) ? "" : t; }
function paragraphs(text, chunks) {
  const cs = (chunks || []).map((c) => ({ t: clean(c.text), ts: c.timestamp || [] })).filter((c) => c.t);
  if (cs.length > 1 && cs.every((c) => c.ts[0] != null)) {
    const out = [[]]; let prevEnd = null;
    for (const c of cs) {
      if (prevEnd != null && c.ts[0] - prevEnd >= PARA_GAP_S) out.push([]);
      out[out.length - 1].push(c.t); prevEnd = c.ts[1] ?? c.ts[0];
    }
    return out.map((p) => p.join(" "));
  }
  const all = cs.length ? cs.map((c) => c.t).join(" ") : clean(text);
  if (!all) return [];
  const sents = all.match(/[^.!?…]+[.!?…]*/g) || [all], out = [];
  for (let i = 0; i < sents.length; i += SENT_PER_PARA) out.push(sents.slice(i, i + SENT_PER_PARA).join(" ").trim());
  return out;
}

// ---- worker ----
let worker = null;
function makeWorker() { worker = new Worker("worker.js", { type: "module" }); worker.onmessage = onMsg; }
let pending = null, readyRes = null, netRes = null;
// Optional ?model= override for evaluation only; default stays in worker.js.
const MODEL_PARAM = new URLSearchParams(location.search).get("model");
const MODELS = { base: "Xenova/whisper-base", small: "Xenova/whisper-small" };
if (MODEL_PARAM) { const k = Object.keys(MODELS).find((k) => MODELS[k] === MODEL_PARAM || k === MODEL_PARAM);
  if (k) $("model").value = k; else { const o = document.createElement("option"); o.value = MODEL_PARAM; o.textContent = MODEL_PARAM; $("model").appendChild(o); $("model").value = MODEL_PARAM; } }
const curModel = () => MODELS[$("model").value] || $("model").value;
const onMsg = (e) => {
  const m = e.data;
  if (m.type === "progress") {
    $("dl").hidden = false; $("dlbar").max = m.total || 1; $("dlbar").value = m.done;
    $("dltext").textContent = T[L].dl.replace("{done}", (m.done / 1048576).toFixed(1)).replace("{total}", (m.total / 1048576).toFixed(1));
  } else if (m.type === "ready") { $("dl").hidden = true; $("firsthint").hidden = true; readyRes && readyRes(); }
  else if (m.type === "netstats") { netRes && netRes(m.entries); }
  else if (m.type === "result" || m.type === "error") { const p = pending; pending = null; p && (m.type === "result" ? p.res(m) : p.rej(new Error(m.message))); }
};
// Guard: if decoding takes far longer than expected (decoder loop), kill the worker and report clearly.
// Test-only hook: ?_test_timeout_ms=N forces a tiny timeout to simulate a hang (used by tests/test_page.py).
let TEST_TIMEOUT_MS = Number(new URLSearchParams(location.search).get("_test_timeout_ms")) || 0;
class TimeoutError extends Error {}
let lastAudio = null; // raw audio of the last run, kept across worker restarts
const TIMEOUT_MIN_S = 30, TIMEOUT_PER_AUDIO_S = 3;
async function asr(audio) {
  await preload(); // model download is not counted against the timeout
  const limit = TEST_TIMEOUT_MS > 0 ? TEST_TIMEOUT_MS : Math.max(TIMEOUT_MIN_S, TIMEOUT_PER_AUDIO_S * audio.length / SR) * 1000;
  return new Promise((res, rej) => {
    const timer = setTimeout(() => { pending = null; worker.terminate(); makeWorker(); rej(new TimeoutError(T[L].timeout)); }, limit);
    pending = { res: (m) => { clearTimeout(timer); res(m); }, rej: (e) => { clearTimeout(timer); rej(e); } }; worker.postMessage({ type: "transcribe", audio, model: curModel(), language: $("speechlang").value || null }, [audio.buffer]); }); }
makeWorker();

async function run(audio) {
  lastAudio = audio; $("fastbtn").hidden = true;
  const n = normalize(audio);
  const a = trim(n.a);
  $("result").innerHTML = ""; $("feedback").hidden = true;
  if (n.peak < MIN_PEAK || a.length < SR * 0.3 || rms(a) < SILENT_RMS || dynRangeDb(n.a) < MIN_DYN_DB) { $("status").textContent = T[L].silent; return { paragraphs: [], skipped: true }; }
  $("status").textContent = T[L].working;
  let r;
  try { r = await asr(a.slice()); }
  catch (e) {
    if (!(e instanceof TimeoutError)) throw e;
    $("status").textContent = T[L].timeout; $("fastbtn").hidden = false;
    return { paragraphs: [], skipped: false, timeout: true, model: curModel() };
  }
  let ps = paragraphs(r.text, r.chunks);
  if (repetitive(ps.join(" "))) ps = [];
  $("status").textContent = ps.length ? "" : T[L].silent;
  for (const p of ps) { const el = document.createElement("p"); el.textContent = p; $("result").appendChild(el); }
  $("feedback").hidden = ps.length === 0;
  return { paragraphs: ps, skipped: false, model: curModel() };
}
// Re-transcribe the SAME kept audio with the fast model (no new dictation).
async function runFast() { if (!lastAudio) return null; $("model").value = "base"; await preload(); return run(lastAudio); }
$("fastbtn").onclick = () => runFast().catch((x) => { $("status").textContent = String(x); });
async function runUrl(url) { return run(await decode(await (await fetch(url)).arrayBuffer())); }

// ---- microphone with auto-stop ----
let rec = null;
const METER_QUIET_RMS = 0.003, MIC_SILENT_MS = 3000;
function showMic(k) { const m = $("micmsg"); m.dataset.k = k; m.textContent = T[L][k]; m.hidden = false; }
async function startRec() {
  $("micmsg").hidden = true;
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); }
  catch (e) {
    const k = ["NotAllowedError", "SecurityError", "PermissionDeniedError"].includes(e && e.name) ? "micdenied"
      : ["NotFoundError", "OverconstrainedError", "DevicesNotFoundError"].includes(e && e.name) ? "micnone" : null;
    if (!k) throw e;
    showMic(k); $("status").textContent = ""; return;
  }
  const ac = new AudioContext(), src = ac.createMediaStreamSource(stream), proc = ac.createScriptProcessor(4096, 1, 1);
  // v2.2: live volume meter (AnalyserNode, 10 updates/s) + "can't hear anything" after >3 s of silence.
  const an = ac.createAnalyser(); an.fftSize = 2048; src.connect(an);
  const buf = new Float32Array(an.fftSize); let quietSince = performance.now();
  $("meter").hidden = false;
  const meterTimer = setInterval(() => {
    an.getFloatTimeDomainData(buf); const v = rms(buf), now = performance.now();
    $("vbar").style.width = Math.min(100, Math.round(Math.sqrt(v / 0.2) * 100)) + "%"; $("vbar").dataset.rms = v.toFixed(5);
    if (v >= METER_QUIET_RMS) { quietSince = now; $("vlabel").hidden = false; if ($("micmsg").dataset.k === "micsilent") $("micmsg").hidden = true; }
    else if (now - quietSince > MIC_SILENT_MS) { $("vlabel").hidden = true; showMic("micsilent"); }
  }, 100);
  const parts = []; let heard = false, lastLoud = performance.now(), t0 = performance.now();
  proc.onaudioprocess = (ev) => {
    const d = ev.inputBuffer.getChannelData(0); parts.push(d.slice());
    const now = performance.now();
    if (rms(d) > SPEECH_RMS) { heard = true; lastLoud = now; }
    if ((heard && now - lastLoud > SILENCE_MS) || now - t0 > MAX_SEC * 1000) stopRec();
  };
  src.connect(proc); proc.connect(ac.destination);
  rec = { stream, ac, proc, parts, meterTimer };
  $("rec").classList.add("rec"); $("rec").disabled = true; $("stop").disabled = false; $("status").textContent = T[L].listening;
}
async function stopRec() {
  if (!rec) return; const r = rec; rec = null;
  clearInterval(r.meterTimer); $("meter").hidden = true; $("vbar").style.width = "0%"; if ($("micmsg").dataset.k === "micsilent") $("micmsg").hidden = true;
  r.proc.disconnect(); r.stream.getTracks().forEach((t) => t.stop());
  const n = r.parts.reduce((s, p) => s + p.length, 0), all = new Float32Array(n); let o = 0;
  for (const p of r.parts) { all.set(p, o); o += p.length; }
  const rate = r.ac.sampleRate; r.ac.close();
  $("rec").classList.remove("rec"); $("rec").disabled = false; $("stop").disabled = true;
  await run(await toMono16k(all, rate));
}
$("rec").onclick = () => startRec().catch((e) => { $("status").textContent = String(e); });
$("stop").onclick = () => stopRec();
$("file").onchange = async (e) => { const f = e.target.files[0]; if (f) run(await decode(await f.arrayBuffer())).catch((x) => { $("status").textContent = String(x); }); };
$("sample").onclick = () => runUrl("eval/06.wav").catch((x) => { $("status").textContent = String(x); });

function preload() { return new Promise((r) => { readyRes = r; worker.postMessage({ type: "load", model: curModel() }); }); }
function netstats() { return new Promise((r) => { netRes = r; worker.postMessage({ type: "netstats" }); }); }
window.v2t = { startRec, stopRec, setTestTimeout: (ms) => { TEST_TIMEOUT_MS = ms; }, runFast, netstats, runUrl, preload, paragraphs, clean, curModel };
applyLang();
