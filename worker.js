// Whisper in a Web Worker via transformers.js (pinned). Approach inspired by xenova/whisper-web (MIT); code written from scratch.
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1";
env.allowLocalModels = false;
const MODEL = "Xenova/whisper-small"; // default (team decision 15.10); page always passes its choice
// v2.3: one shared pipeline promise per model, so concurrent "load" requests (record + sample, or a
// model switch during download) never start a second download and every caller gets "ready".
const pipes = {};
let modelId = MODEL;
function load(id = modelId) {
  if (pipes[id]) return pipes[id];
  const files = {};
  pipes[id] = pipeline("automatic-speech-recognition", id, {
    dtype: "q8",
    progress_callback: (p) => {
      if (p.status === "progress" && p.file) {
        files[p.file] = { loaded: p.loaded || 0, total: p.total || 0 };
        let done = 0, total = 0;
        for (const f of Object.values(files)) { done += f.loaded; total += f.total; }
        postMessage({ type: "progress", done, total, model: id });
      }
    },
  });
  pipes[id].catch(() => { delete pipes[id]; });
  return pipes[id];
}
self.onmessage = async (e) => {
  const { type, audio, language, model } = e.data;
  if (model) modelId = model;
  const id = modelId;
  try {
    if (type === "load") { await load(id); postMessage({ type: "ready", model: id }); return; }
    if (type === "netstats") { // eval aid: resource timing of this worker (read-only)
      postMessage({ type: "netstats", entries: performance.getEntriesByType("resource").map((r) => ({ name: r.name, transferSize: r.transferSize, encodedBodySize: r.encodedBodySize, decodedBodySize: r.decodedBodySize })) });
      return;
    }
    if (type === "transcribe") {
      const p = await load(id);
      const out = await p(audio, {
        language: language || null, task: "transcribe",
        chunk_length_s: 30, stride_length_s: 5, return_timestamps: true,
        // Guard against decoder loops: per 30 s window, ~12 tokens/s of fast Russian speech + margin, capped below Whisper's 448.
        max_new_tokens: Math.min(440, Math.ceil(12 * Math.min(30, audio.length / 16000)) + 32),
      });
      postMessage({ type: "result", text: out.text, chunks: out.chunks || [] });
    }
  } catch (err) { if (type === "load") { postMessage({ type: "loaderror", model: id, message: String(err && err.message || err) }); return; } postMessage({ type: "error", message: String(err && err.message || err) }); }
};
