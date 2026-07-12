// H5 聊天页逻辑（微信风格 + 流式 + 语音）
// 语音输入走后端本地 Whisper：浏览器录音 -> 解码为 16k 单声道 WAV -> POST /api/transcribe -> 回填发送
const $ = (s) => document.querySelector(s);

const slug = location.pathname.split("/c/")[1] || "";
let history = []; // [{role, content}]
let ttsOn = true;
let listening = false;
let currentAudio = null; // 当前正在播放的 Edge TTS 音频，用于随时停止

async function init() {
  const res = await fetch("/api/agents/" + slug);
  if (!res.ok) {
    $("#messages").innerHTML = '<div class="msg left"><div class="bubble">智能体不存在或已删除。</div></div>';
    return;
  }
  const a = await res.json();
  $("#agent-name").textContent = a.name;
  if (a.opening) {
    addMsg("left", a.opening);
    // 问候语播报：浏览器自动播放策略可能拦截首屏语音，
    // 先尝试立即播放，失败则等首次用户交互（点击/按键）后再播
    if (ttsOn) {
      const ok = await speak(a.opening);
      if (!ok) {
        const onFirst = () => { speak(a.opening); };
        document.addEventListener("click", onFirst, { once: true });
        document.addEventListener("keydown", onFirst, { once: true });
      }
    }
  }
}

function addMsg(side, text) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + side;
  const ava = document.createElement("div");
  ava.className = "ava";
  ava.innerHTML = side === "left" ? (window.__agentAvatarImg || "🙂") : "🧑";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(ava);
  wrap.appendChild(bubble);
  $("#messages").appendChild(wrap);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return bubble;
}

async function send() {
  stopSpeaking(); // 发新消息时先停掉上一轮可能还在播放的语音
  let hadError = false;
  const input = $("#input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMsg("right", text);
  history.push({ role: "user", content: text });

  // 占位泡泡（流式）
  const bubble = addMsg("left", "");
  bubble.classList.add("typing");

  const resp = await fetch("/api/agents/" + slug + "/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: history, stream: true }),
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let full = "";
  bubble.classList.remove("typing");
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    chunk.split("\n\n").forEach((line) => {
      if (line.startsWith("data: ")) {
        try {
          const d = JSON.parse(line.slice(6));
          full += d.content;
          if (d.error) hadError = true;
          bubble.textContent = full;
          $("#messages").scrollTop = $("#messages").scrollHeight;
        } catch (e) {}
      }
    });
  }
  history.push({ role: "assistant", content: full });
  if (ttsOn && !hadError) speak(full);
}

// 立即停止当前正在播放的语音（Edge TTS 的 Audio 或浏览器原生 speechSynthesis）
function stopSpeaking() {
  if (currentAudio) {
    try { currentAudio.pause(); } catch (e) {}
    currentAudio = null;
  }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
}

// 语音播报：优先后端 Edge TTS，失败回退浏览器 speechSynthesis。返回是否成功触发播放
async function speak(text) {
  if (!text) return false;
  try {
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudio = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (currentAudio === audio) currentAudio = null;
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        if (currentAudio === audio) currentAudio = null;
      };
      try {
        await audio.play();
        return true;
      } catch (e) {
        currentAudio = null;
      }
    }
  } catch (e) {
    // 后端不可用，走兜底
  }
  // 兜底：浏览器原生语音
  return speakFallback(text);
}

function speakFallback(text) {
  if (!("speechSynthesis" in window)) return false;
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-CN";
    u.rate = 1;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
    return true;
  } catch (e) {
    return false;
  }
}

// 把 16kHz 单声道 Float32 采样编码为 WAV（后端 soundfile 直接读取，无需 ffmpeg）
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (off, s) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);        // PCM
  view.setUint16(22, 1, true);        // 单声道
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);       // 16bit
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}

// 把任意采样率的音频重采样到 16kHz 单声道（Whisper 要求）
function resampleTo16k(audioBuffer) {
  const offline = new OfflineAudioContext(1, Math.ceil(audioBuffer.duration * 16000), 16000);
  const src = offline.createBufferSource();
  src.buffer = audioBuffer;
  src.connect(offline.destination);
  src.start();
  return offline.startRendering().then((rendered) => rendered.getChannelData(0));
}

// 语音输入：浏览器录音 -> 本地解码为 WAV -> 发后端本地 Whisper 转写
async function setupVoice() {
  const mic = $("#mic");
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    mic.title = "当前浏览器不支持语音输入";
    mic.onclick = () => alert("当前浏览器不支持录音，请使用较新版本的 Chrome / Edge / Safari");
    return;
  }
  let recorder = null;
  let chunks = [];
  let stream = null;

  mic.onclick = async () => {
    if (listening) {
      recorder && recorder.stop();
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      alert("无法访问麦克风：" + (e && e.message ? e.message : e));
      return;
    }
    chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (ev) => ev.data && chunks.push(ev.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      listening = false;
      mic.classList.remove("listening");
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      await transcribe(blob);
    };
    listening = true;
    mic.classList.add("listening");
    recorder.start();
  };

  async function transcribe(blob) {
    try {
      $("#input").placeholder = "识别中…";
      const arrayBuffer = await blob.arrayBuffer();
      const AC = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AC();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
      const samples = await resampleTo16k(audioBuffer);
      const wav = encodeWAV(samples, 16000);
      const fd = new FormData();
      fd.append("file", wav, "speech.wav");
      fd.append("slug", slug);
      const res = await fetch("/api/transcribe", { method: "POST", body: fd });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();
      const text = (json.text || "").trim();
      $("#input").placeholder = "说点什么…";
      if (text) {
        $("#input").value = text;
        send();
      } else {
        $("#input").placeholder = "没听清，请再说一次或打字";
      }
    } catch (e) {
      console.error("语音识别失败", e);
      $("#input").placeholder = "语音识别失败，请打字输入";
    }
  }
}

$("#send").onclick = send;
$("#input").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
$("#tts-toggle").onclick = () => {
  ttsOn = !ttsOn;
  if (!ttsOn) stopSpeaking(); // 关闭播报时立即停止当前正在播放的语音
  $("#tts-toggle").classList.toggle("off", !ttsOn);
  $("#tts-toggle").textContent = ttsOn ? "🔊" : "🔇";
};

// 加载头像
(async () => {
  try {
    const res = await fetch("/api/agents/" + slug);
    if (res.ok) {
      const a = await res.json();
      if (a.avatar) window.__agentAvatarImg = `<img src="/data/agents/${a.slug}/${a.avatar}" />`;
    }
  } catch (e) {}
  setupVoice();
  init();
})();
