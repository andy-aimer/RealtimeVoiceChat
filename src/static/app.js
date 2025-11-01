(function() {
  const originalLog = console.log.bind(console);
  console.log = (...args) => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    const ms = String(now.getMilliseconds()).padStart(3, '0');
    originalLog(
      `[${hh}:${mm}:${ss}.${ms}]`,
      ...args
    );
  };
})();

// =============================================================================
// Phase 2 P3: WebSocket Client with Reconnection (T087-T092)
// =============================================================================

/**
 * Exponential backoff calculator for retry operations.
 * Mirrors server-side ExponentialBackoff utility.
 */
class ExponentialBackoff {
  constructor(initialDelay = 1000, maxDelay = 30000, maxAttempts = 10) {
    this.initialDelay = initialDelay;  // milliseconds
    this.maxDelay = maxDelay;
    this.maxAttempts = maxAttempts;
    this.attempt = 0;
  }

  nextDelay() {
    const delay = Math.min(
      this.initialDelay * Math.pow(2, this.attempt),
      this.maxDelay
    );
    this.attempt++;
    return delay;
  }

  shouldGiveUp() {
    return this.attempt >= this.maxAttempts;
  }

  reset() {
    this.attempt = 0;
  }

  getAttempt() {
    return this.attempt;
  }
}

/**
 * WebSocket client with automatic reconnection support.
 * Manages session persistence via localStorage and exponential backoff.
 */
class WebSocketClient {
  constructor(url, options = {}) {
    this.baseUrl = url;
    this.socket = null;
    this.sessionId = null;
    this.backoff = new ExponentialBackoff(1000, 30000, 10);
    this.reconnectTimer = null;
    this.intentionallyClosed = false;
    this.isReconnecting = false;
    
    // Callbacks
    this.onopen = options.onopen || (() => {});
    this.onmessage = options.onmessage || (() => {});
    this.onclose = options.onclose || (() => {});
    this.onerror = options.onerror || (() => {});
    this.onreconnecting = options.onreconnecting || (() => {});
    this.onreconnected = options.onreconnected || (() => {});
    this.onreconnectfailed = options.onreconnectfailed || (() => {});
    
    // Load session ID from localStorage
    this.loadSessionId();
  }

  loadSessionId() {
    try {
      this.sessionId = localStorage.getItem('voicechat_session_id');
      if (this.sessionId) {
        console.log(`📦 Loaded session ID from storage: ${this.sessionId.substring(0, 8)}...`);
      }
    } catch (e) {
      console.warn('Failed to load session ID from localStorage:', e);
    }
  }

  saveSessionId(sessionId) {
    this.sessionId = sessionId;
    try {
      localStorage.setItem('voicechat_session_id', sessionId);
      console.log(`💾 Saved session ID to storage: ${sessionId.substring(0, 8)}...`);
    } catch (e) {
      console.warn('Failed to save session ID to localStorage:', e);
    }
  }

  clearSessionId() {
    this.sessionId = null;
    try {
      localStorage.removeItem('voicechat_session_id');
      console.log('🗑️ Cleared session ID from storage');
    } catch (e) {
      console.warn('Failed to clear session ID from localStorage:', e);
    }
  }

  buildUrl() {
    let url = this.baseUrl;
    if (this.sessionId) {
      url += `?session_id=${encodeURIComponent(this.sessionId)}`;
    }
    return url;
  }

  connect() {
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      console.log('⚠️ Already connected or connecting');
      return;
    }

    this.intentionallyClosed = false;
    const url = this.buildUrl();
    console.log(`🔌 Connecting to ${url}`);

    try {
      this.socket = new WebSocket(url);
      this.setupSocketHandlers();
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.scheduleReconnect();
    }
  }

  setupSocketHandlers() {
    this.socket.onopen = () => {
      console.log('✅ WebSocket connected');
      this.backoff.reset();
      this.isReconnecting = false;
      
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      
      this.onopen();
    };

    this.socket.onmessage = (event) => {
      // Handle session management messages
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data);
          
          // Phase 2 P3: Handle session_id message (T089)
          if (msg.type === 'session_id') {
            this.saveSessionId(msg.session_id);
            console.log(`🆔 Received new session ID: ${msg.session_id.substring(0, 8)}...`);
          }
          // Phase 2 P3: Handle session_restored message (T090)
          else if (msg.type === 'session_restored') {
            console.log(`🔄 Session restored: ${msg.session_id.substring(0, 8)}... (${msg.message_count} messages)`);
            this.onreconnected(msg);
          }
        } catch (e) {
          // Not JSON or parsing failed, pass through
        }
      }
      
      this.onmessage(event);
    };

    this.socket.onclose = (event) => {
      console.log(`❌ WebSocket closed (code: ${event.code}, reason: ${event.reason || 'none'})`);
      this.socket = null;
      
      if (!this.intentionallyClosed) {
        this.scheduleReconnect();
      }
      
      this.onclose(event);
    };

    this.socket.onerror = (error) => {
      console.error('💥 WebSocket error:', error);
      this.onerror(error);
    };
  }

  scheduleReconnect() {
    if (this.intentionallyClosed) {
      console.log('⏹️ Intentionally closed, not reconnecting');
      return;
    }

    if (this.backoff.shouldGiveUp()) {
      console.error(`❌ Max reconnection attempts (${this.backoff.maxAttempts}) reached. Giving up.`);
      this.onreconnectfailed();
      return;
    }

    const delay = this.backoff.nextDelay();
    const attempt = this.backoff.getAttempt();
    
    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${attempt}/${this.backoff.maxAttempts})...`);
    this.isReconnecting = true;
    this.onreconnecting(attempt, this.backoff.maxAttempts, delay);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(data);
      return true;
    }
    console.warn('⚠️ Cannot send: WebSocket not open');
    return false;
  }

  close() {
    this.intentionallyClosed = true;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    console.log('⏹️ WebSocket closed intentionally');
  }

  get readyState() {
    return this.socket ? this.socket.readyState : WebSocket.CLOSED;
  }

  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }
}

// =============================================================================
// Original Application Code (with WebSocketClient integration)
// =============================================================================

const statusDiv = document.getElementById("status");
const messagesDiv = document.getElementById("messages");
const speedSlider = document.getElementById("speedSlider");
speedSlider.disabled = true;  // start disabled

let wsClient = null;  // Phase 2 P3: Changed from 'socket' to 'wsClient'
let audioContext = null;
let mediaStream = null;
let micWorkletNode = null;
let ttsWorkletNode = null;

let isTTSPlaying = false;
let ignoreIncomingTTS = false;

let chatHistory = [];
let typingUser = "";
let typingAssistant = "";

// --- batching + fixed 8‑byte header setup ---
const BATCH_SAMPLES = 2048;
const HEADER_BYTES  = 8;
const FRAME_BYTES   = BATCH_SAMPLES * 2;
const MESSAGE_BYTES = HEADER_BYTES + FRAME_BYTES;

const bufferPool = [];
let batchBuffer = null;
let batchView = null;
let batchInt16 = null;
let batchOffset = 0;

function initBatch() {
  if (!batchBuffer) {
    batchBuffer = bufferPool.pop() || new ArrayBuffer(MESSAGE_BYTES);
    batchView   = new DataView(batchBuffer);
    batchInt16  = new Int16Array(batchBuffer, HEADER_BYTES);
    batchOffset = 0;
  }
}

function flushBatch() {
  const ts = Date.now() & 0xFFFFFFFF;
  batchView.setUint32(0, ts, false);
  const flags = isTTSPlaying ? 1 : 0;
  batchView.setUint32(4, flags, false);

  if (wsClient && wsClient.isConnected()) {
    wsClient.send(batchBuffer);
  }

  bufferPool.push(batchBuffer);
  batchBuffer = null;
}

function flushRemainder() {
  if (batchOffset > 0) {
    for (let i = batchOffset; i < BATCH_SAMPLES; i++) {
      batchInt16[i] = 0;
    }
    flushBatch();
  }
}

function initAudioContext() {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
}

function base64ToInt16Array(b64) {
  const raw = atob(b64);
  const buf = new ArrayBuffer(raw.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < raw.length; i++) {
    view[i] = raw.charCodeAt(i);
  }
  return new Int16Array(buf);
}

async function startRawPcmCapture() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: { ideal: 24000 },
        channelCount: 1,
        echoCancellation: true,
        // autoGainControl: true,
        noiseSuppression: true
      }
    });
    mediaStream = stream;
    initAudioContext();
    await audioContext.audioWorklet.addModule('/static/pcmWorkletProcessor.js');
    micWorkletNode = new AudioWorkletNode(audioContext, 'pcm-worklet-processor');

    micWorkletNode.port.onmessage = ({ data }) => {
      const incoming = new Int16Array(data);
      let read = 0;
      while (read < incoming.length) {
        initBatch();
        const toCopy = Math.min(
          incoming.length - read,
          BATCH_SAMPLES - batchOffset
        );
        batchInt16.set(
          incoming.subarray(read, read + toCopy),
          batchOffset
        );
        batchOffset += toCopy;
        read       += toCopy;
        if (batchOffset === BATCH_SAMPLES) {
          flushBatch();
        }
      }
    };

    const source = audioContext.createMediaStreamSource(stream);
    source.connect(micWorkletNode);
    statusDiv.textContent = "Recording...";
  } catch (err) {
    statusDiv.textContent = "Mic access denied.";
    console.error(err);
  }
}

async function setupTTSPlayback() {
  await audioContext.audioWorklet.addModule('/static/ttsPlaybackProcessor.js');
  ttsWorkletNode = new AudioWorkletNode(
    audioContext,
    'tts-playback-processor'
  );

  ttsWorkletNode.port.onmessage = (event) => {
    const { type } = event.data;
    if (type === 'ttsPlaybackStarted') {
      if (!isTTSPlaying && wsClient && wsClient.isConnected()) {
        isTTSPlaying = true;
        console.log(
          "TTS playback started. Reason: ttsWorkletNode Event ttsPlaybackStarted."
        );
        wsClient.send(JSON.stringify({ type: 'tts_start' }));
      }
    } else if (type === 'ttsPlaybackStopped') {
      if (isTTSPlaying && wsClient && wsClient.isConnected()) {
        isTTSPlaying = false;
        console.log(
          "TTS playback stopped. Reason: ttsWorkletNode Event ttsPlaybackStopped."
        );
        wsClient.send(JSON.stringify({ type: 'tts_stop' }));
      }
    }
  };
  ttsWorkletNode.connect(audioContext.destination);
}

function cleanupAudio() {
  if (micWorkletNode) {
    micWorkletNode.disconnect();
    micWorkletNode = null;
  }
  if (ttsWorkletNode) {
    ttsWorkletNode.disconnect();
    ttsWorkletNode = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getAudioTracks().forEach(track => track.stop());
    mediaStream = null;
  }
}

function renderMessages() {
  messagesDiv.innerHTML = "";
  chatHistory.forEach(msg => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${msg.role}`;
    bubble.textContent = msg.content;
    messagesDiv.appendChild(bubble);
  });
  if (typingUser) {
    const typing = document.createElement("div");
    typing.className = "bubble user typing";
    typing.innerHTML = typingUser + '<span style="opacity:.6;">✏️</span>';
    messagesDiv.appendChild(typing);
  }
  if (typingAssistant) {
    const typing = document.createElement("div");
    typing.className = "bubble assistant typing";
    typing.innerHTML = typingAssistant + '<span style="opacity:.6;">✏️</span>';
    messagesDiv.appendChild(typing);
  }
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function handleJSONMessage({ type, content }) {
  if (type === "partial_user_request") {
    typingUser = content?.trim() ? escapeHtml(content) : "";
    renderMessages();
    return;
  }
  if (type === "final_user_request") {
    if (content?.trim()) {
      chatHistory.push({ role: "user", content, type: "final" });
    }
    typingUser = "";
    renderMessages();
    return;
  }
  if (type === "partial_assistant_answer") {
    typingAssistant = content?.trim() ? escapeHtml(content) : "";
    renderMessages();
    return;
  }
  if (type === "final_assistant_answer") {
    if (content?.trim()) {
      chatHistory.push({ role: "assistant", content, type: "final" });
    }
    typingAssistant = "";
    renderMessages();
    return;
  }
  // T037: Handle voice change notifications from server
  if (type === "voice_changed") {
    const voiceId = content;
    console.log(`🎤📢 Voice change notification received: ${voiceId}`);
    
    // Update dropdown to reflect the change
    const voiceSelect = document.getElementById('voiceSelect');
    if (voiceSelect) {
      voiceSelect.value = voiceId;
    }
    
    // Show notification in chat
    addMessage('system', `Voice changed to: ${voiceId}`);
    return;
  }
  
  if (type === "tts_chunk") {
    if (ignoreIncomingTTS) return;
    const int16Data = base64ToInt16Array(content);
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage(int16Data);
    }
    return;
  }
  if (type === "tts_interruption") {
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage({ type: "clear" });
    }
    isTTSPlaying = false;
    ignoreIncomingTTS = false;
    return;
  }
  if (type === "stop_tts") {
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage({ type: "clear" });
    }
    isTTSPlaying = false;
    ignoreIncomingTTS = true;
    console.log("TTS playback stopped. Reason: tts_interruption.");
    if (wsClient && wsClient.isConnected()) {
      wsClient.send(JSON.stringify({ type: 'tts_stop' }));
    }
    return;
  }
}

function escapeHtml(str) {
  return (str ?? '')
    .replace(/&/g, "&amp;")
    .replace(/</g, "<")
    .replace(/>/g, ">")
    .replace(/"/g, "&quot;");
}

// UI Controls

document.getElementById("clearBtn").onclick = () => {
  chatHistory = [];
  typingUser = typingAssistant = "";
  renderMessages();
  if (wsClient && wsClient.isConnected()) {
    wsClient.send(JSON.stringify({ type: 'clear_history' }));
  }
};

speedSlider.addEventListener("input", (e) => {
  const speedValue = parseInt(e.target.value);
  if (wsClient && wsClient.isConnected()) {
    wsClient.send(JSON.stringify({
      type: 'set_speed',
      speed: speedValue
    }));
  }
  console.log("Speed setting changed to:", speedValue);
});

// =============================================================================
// Phase 2 P3: Connection Status UI (T091)
// =============================================================================

function updateConnectionStatus(status, message) {
  statusDiv.textContent = message;
  statusDiv.className = `status-${status}`;  // For CSS styling
}

// =============================================================================
// UI Controls
// =============================================================================

document.getElementById("startBtn").onclick = async () => {
  if (wsClient && wsClient.isConnected()) {
    statusDiv.textContent = "Already recording.";
    return;
  }
  
  updateConnectionStatus('connecting', 'Initializing connection...');

  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProto}//${location.host}/ws`;
  
  // Phase 2 P3: Create WebSocketClient with reconnection support
  wsClient = new WebSocketClient(wsUrl, {
    onopen: async () => {
      updateConnectionStatus('connected', 'Connected. Activating mic and TTS…');
      await startRawPcmCapture();
      await setupTTSPlayback();
      speedSlider.disabled = false;
      updateConnectionStatus('recording', 'Recording...');
    },
    
    onmessage: (evt) => {
      if (typeof evt.data === "string") {
        try {
          const msg = JSON.parse(evt.data);
          handleJSONMessage(msg);
        } catch (e) {
          console.error("Error parsing message:", e);
        }
      }
    },
    
    onclose: () => {
      if (wsClient && !wsClient.intentionallyClosed) {
        updateConnectionStatus('disconnected', 'Connection lost. Reconnecting...');
      } else {
        updateConnectionStatus('stopped', 'Connection closed.');
        flushRemainder();
        cleanupAudio();
        speedSlider.disabled = true;
      }
    },
    
    onerror: (err) => {
      console.error('WebSocket error:', err);
    },
    
    onreconnecting: (attempt, maxAttempts, delay) => {
      updateConnectionStatus(
        'reconnecting',
        `Reconnecting... (attempt ${attempt}/${maxAttempts}, retry in ${delay}ms)`
      );
    },
    
    onreconnected: (msg) => {
      updateConnectionStatus('reconnected', 'Reconnected! Session restored.');
      console.log(`🔄 Session restored with ${msg.message_count} messages`);
    },
    
    onreconnectfailed: () => {
      updateConnectionStatus('failed', 'Reconnection failed. Please refresh the page.');
      cleanupAudio();
      speedSlider.disabled = true;
    }
  });
  
  wsClient.connect();
};

document.getElementById("stopBtn").onclick = () => {
  if (wsClient) {
    flushRemainder();
    wsClient.close();
    wsClient = null;
  }
  cleanupAudio();
  updateConnectionStatus('stopped', 'Stopped.');
};

document.getElementById("copyBtn").onclick = () => {
  const text = chatHistory
    .map(msg => `${msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}: ${msg.content}`)
    .join('\n');
  
  navigator.clipboard.writeText(text)
    .then(() => console.log("Conversation copied to clipboard"))
    .catch(err => console.error("Copy failed:", err));
};

// First render
renderMessages();

// =============================================================================
// T036: Voice Selection Feature
// =============================================================================

/**
 * Fetches available voices from /tts/voices endpoint and populates dropdown
 */
async function loadVoices() {
  const voiceSelect = document.getElementById('voiceSelect');
  
  try {
    const response = await fetch('/tts/voices');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Clear loading option
    voiceSelect.innerHTML = '';
    
    // Populate dropdown with available voices
    data.voices.forEach(voice => {
      const option = document.createElement('option');
      option.value = voice.voice_id;
      option.textContent = `${voice.display_name} (${voice.gender})`;
      
      // Mark default voice as selected
      if (voice.voice_id === data.default_voice) {
        option.selected = true;
      }
      
      voiceSelect.appendChild(option);
    });
    
    console.log(`🎤 Loaded ${data.voices.length} voices, default: ${data.default_voice}`);
  } catch (error) {
    console.error('Failed to load voices:', error);
    voiceSelect.innerHTML = '<option value="">Voice selection unavailable</option>';
  }
}

/**
 * Handles voice selection change by calling PATCH /tts/config endpoint
 */
async function changeVoice(voiceId) {
  try {
    const response = await fetch('/tts/config', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        default_voice: voiceId
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    console.log(`🎤✅ Voice changed to: ${result.current_config.default_voice}`);
    
    // T037: Voice change will be communicated via WebSocket message
    addMessage('system', `Voice changed to: ${voiceId}`);
    
  } catch (error) {
    console.error('Failed to change voice:', error);
    addMessage('system', `Failed to change voice: ${error.message}`);
  }
}

// Voice select dropdown handler
document.getElementById('voiceSelect').addEventListener('change', (event) => {
  const selectedVoice = event.target.value;
  if (selectedVoice) {
    changeVoice(selectedVoice);
  }
});

// Load voices when page loads
loadVoices();
