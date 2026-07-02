/**
 * Front of House Voice Terminal & Control Room Dashboard
 * Built with native modern Vanilla JS & Web Audio APIs
 */

// Global state variables
let state = 'IDLE'; // 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'
let ws = null;
let audioCtx = null;
let micStream = null;
let micProcessor = null;
let pcmPlayQueueNextTime = 0;
let isMuted = false;

// Audio analyser nodes for visualizer
let inputAnalyser = null;
let outputAnalyser = null;
let visualizerAnalyser = null; // Currently active analyser node

// Status polling interval
let statusInterval = null;

// UI DOM references
const connectionBeacon = document.getElementById('connection-beacon');
const systemStatusBadge = document.getElementById('system-status-badge');
const micBtn = document.getElementById('mic-btn');
const toggleChatBtn = document.getElementById('toggle-chat-btn');
const chatDrawer = document.getElementById('chat-drawer');
const chatHistory = document.getElementById('chat-history-container');
const chatInputForm = document.getElementById('chat-input-form');
const chatTextInput = document.getElementById('chat-text-input');
const subtitlesText = document.getElementById('transcript-subtitles');

// Dashboard DOM references
const onAirCameraTitle = document.getElementById('on-air-camera-title');
const onAirFrameDesc = document.getElementById('on-air-frame-desc');
const telemetryPan = document.getElementById('telemetry-pan');
const telemetryTilt = document.getElementById('telemetry-tilt');
const telemetryZoom = document.getElementById('telemetry-zoom');
const vuHostBar = document.getElementById('vu-host-bar');
const vuHostDb = document.getElementById('vu-host-db');
const vuGuestBar = document.getElementById('vu-guest-bar');
const vuGuestDb = document.getElementById('vu-guest-db');
const startShowBtn = document.getElementById('start-show-btn');
const stopShowBtn = document.getElementById('stop-show-btn');
const rundownList = document.getElementById('rundown-list-container');
const directorConsoleLog = document.getElementById('director-console-log');

// Sound control icons
const soundOnIcon = document.getElementById('sound-on-icon');
const soundOffIcon = document.getElementById('sound-off-icon');
const toggleMuteBtn = document.getElementById('toggle-mute-btn');

// --- 1. INITIALIZE WEB AUDIO ---
function initAudio() {
    if (audioCtx) return;
    
    // Create AudioContext with 24000Hz sampling rate (native to Gemini Live output)
    audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    
    // Create output analyser node for visualizer
    outputAnalyser = audioCtx.createAnalyser();
    outputAnalyser.fftSize = 256;
    outputAnalyser.connect(audioCtx.destination);
    
    // Default visualizer to output analyser so it breathes or reacts to playing sounds
    visualizerAnalyser = outputAnalyser;
}

// --- 2. MICROPHONE CAPTURE & DOWNSAMPLING ---
async function startMicrophone() {
    initAudio();
    if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
    }
    
    try {
        // Request mic access
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                channelCount: 1
            }
        });
        
        const micSource = audioCtx.createMediaStreamSource(micStream);
        
        // Create input analyser for visualizer
        inputAnalyser = audioCtx.createAnalyser();
        inputAnalyser.fftSize = 256;
        micSource.connect(inputAnalyser);
        
        // Create script processor to downsample PCM chunks
        // Buffer size 2048, 1 input channel, 1 output channel
        micProcessor = audioCtx.createScriptProcessor(2048, 1, 1);
        
        micProcessor.onaudioprocess = (e) => {
            if (state !== 'LISTENING' || !ws || ws.readyState !== WebSocket.OPEN) return;
            
            const inputFloat32 = e.inputBuffer.getChannelData(0);
            const nativeSampleRate = e.inputBuffer.sampleRate;
            
            // Decimation ratio to reach 16000Hz (Gemini Live input standard)
            const ratio = nativeSampleRate / 16000;
            const downsampledLength = Math.floor(inputFloat32.length / ratio);
            const pcmInt16 = new Int16Array(downsampledLength);
            
            // Downsample and convert to 16-bit mono little-endian PCM
            for (let i = 0; i < downsampledLength; i++) {
                const nativeIndex = Math.floor(i * ratio);
                const s = Math.max(-1.0, Math.min(1.0, inputFloat32[nativeIndex]));
                // Scale Float32 [-1, 1] to Int16 range
                pcmInt16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            
            // Send binary PCM chunk over websocket
            ws.send(pcmInt16.buffer);
        };
        
        micSource.connect(micProcessor);
        micProcessor.connect(audioCtx.destination); // Required to trigger onaudioprocess in some browsers
        
    } catch (err) {
        console.error("Microphone access denied or failed:", err);
        subtitlesText.textContent = "Microphone access denied. Fall back to text chat.";
        updateVoiceState('IDLE');
    }
}

function stopMicrophone() {
    if (micProcessor) {
        micProcessor.disconnect();
        micProcessor = null;
    }
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }
    if (inputAnalyser) {
        inputAnalyser = null;
    }
}

// --- 3. SPEECH PLAYBACK QUEUE (PCM SCHEDULER) ---
function playPCMChunk(arrayBuffer) {
    if (isMuted || !audioCtx) return;
    
    // Convert 16-bit PCM bytes to Float32 array
    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
    }
    
    // Create AudioBuffer (mono, 24000Hz sampling rate)
    const audioBuffer = audioCtx.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);
    
    // Create AudioBufferSourceNode
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    
    // Route through output analyser (drives the canvas speaking waves!)
    source.connect(outputAnalyser);
    
    // Schedule back-to-back to prevent clicking/gaps
    const currentTime = audioCtx.currentTime;
    if (pcmPlayQueueNextTime < currentTime) {
        // Sync queue time if it fell behind actual timeline
        pcmPlayQueueNextTime = currentTime;
    }
    
    source.start(pcmPlayQueueNextTime);
    pcmPlayQueueNextTime += audioBuffer.duration;
}

// --- 4. WEBSOCKET PROXY CONNECTOR ---
function connectWebSocket() {
    const wsUrl = `ws://${window.location.host}/api/ws`;
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = () => {
        console.log("WebSocket connected.");
        connectionBeacon.className = "glowing-beacon connected";
        systemStatusBadge.textContent = "HOST CONNECTED";
    };
    
    ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            // Binary audio chunk received from Gemini Live
            if (state !== 'SPEAKING') {
                updateVoiceState('SPEAKING');
            }
            playPCMChunk(event.data);
        } else {
            // Text subtitle/transcript payload
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'text') {
                    handleFOHSpeechTranscript(msg.text);
                }
            } catch (err) {
                console.error("Error parsing websocket JSON:", err);
            }
        }
    };
    
    ws.onclose = () => {
        console.log("WebSocket disconnected. Retrying in 5 seconds...");
        connectionBeacon.className = "glowing-beacon";
        systemStatusBadge.textContent = "OFFLINE";
        updateVoiceState('IDLE');
        setTimeout(connectWebSocket, 5000);
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}

// --- 5. STATE MACHINE COORDINATOR ---
function updateVoiceState(newState) {
    state = newState;
    console.log(`Voice State -> ${state}`);
    
    // Update active badges
    document.querySelectorAll('.status-badge').forEach(badge => badge.classList.remove('active'));
    
    // Reset buttons/visuals
    micBtn.className = "glowing-mic-btn " + state.toLowerCase();
    
    if (state === 'IDLE') {
        document.getElementById('badge-idle').classList.add('active');
        visualizerAnalyser = outputAnalyser; // Animate breathing wave
        stopMicrophone();
    } else if (state === 'LISTENING') {
        document.getElementById('badge-listening').classList.add('active');
        subtitlesText.textContent = "Listening to your voice... Speak now!";
        visualizerAnalyser = inputAnalyser; // Animate microphone waves
    } else if (state === 'THINKING') {
        document.getElementById('badge-thinking').classList.add('active');
        subtitlesText.textContent = "Front of House is thinking...";
        visualizerAnalyser = outputAnalyser;
        stopMicrophone();
    } else if (state === 'SPEAKING') {
        document.getElementById('badge-speaking').classList.add('active');
        visualizerAnalyser = outputAnalyser; // Animate based on playing audio
        stopMicrophone();
    }
}

// Subtitles & transcription coordination
let activeAssistantSpeech = "";
let assistantBubble = null;

function handleFOHSpeechTranscript(text) {
    if (state !== 'SPEAKING') {
        updateVoiceState('SPEAKING');
    }
    
    // Accumulate spoken transcript
    activeAssistantSpeech += text;
    subtitlesText.textContent = activeAssistantSpeech;
    
    // Live update the scrolling chat history bubble
    if (!assistantBubble) {
        assistantBubble = document.createElement('div');
        assistantBubble.className = "chat-bubble assistant";
        chatHistory.appendChild(assistantBubble);
    }
    assistantBubble.textContent = activeAssistantSpeech;
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // Set a timeout to clear / reset once speaking completes
    resetSpeechTimeout();
}

let speechFinishedTimeout = null;
function resetSpeechTimeout() {
    if (speechFinishedTimeout) {
        clearTimeout(speechFinishedTimeout);
    }
    speechFinishedTimeout = setTimeout(() => {
        // Speech finished (no new text or binary received in 1.2s)
        console.log("FOH finished speaking.");
        activeAssistantSpeech = "";
        assistantBubble = null;
        updateVoiceState('IDLE');
    }, 1500);
}

// --- 6. CANVAS OVERLAPPING SINE WAVES ---
const canvas = document.getElementById('visualizer-canvas');
const ctx = canvas.getContext('2d');

// Set canvas bounds
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

let wavePhase = 0;

function drawVisualizer() {
    requestAnimationFrame(drawVisualizer);
    
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    
    // Extract real-time frequency/amplitude data
    let amplitudeFactor = 1.0;
    if (visualizerAnalyser) {
        const dataArray = new Uint8Array(visualizerAnalyser.frequencyBinCount);
        visualizerAnalyser.getByteTimeDomainData(dataArray);
        
        // Compute average root-mean-square (RMS) amplitude
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            const val = (dataArray[i] - 128) / 128;
            sum += val * val;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        // Map average amplitude to a styling factor
        amplitudeFactor = 1.0 + rms * 6.0;
    }
    
    // Wave states parameters
    let waveCount = 4;
    let baseAmplitude = 8;
    let waveSpeed = 0.015;
    let frequencyFactor = 1;
    
    if (state === 'IDLE') {
        baseAmplitude = 6;
        waveSpeed = 0.01;
        waveCount = 3;
    } else if (state === 'LISTENING') {
        baseAmplitude = 10 * amplitudeFactor;
        waveSpeed = 0.025;
    } else if (state === 'THINKING') {
        baseAmplitude = 4;
        waveSpeed = 0.06;
        frequencyFactor = 2.5; // Condensed pulsing frequencies
    } else if (state === 'SPEAKING') {
        baseAmplitude = 12 * amplitudeFactor;
        waveSpeed = 0.025;
    }
    
    wavePhase += waveSpeed;
    
    // Render 4 overlapping animated sine waves
    for (let i = 0; i < waveCount; i++) {
        ctx.beginPath();
        
        // Distribute colors across Gemini colors gradient
        let gradient = ctx.createLinearGradient(0, 0, width, 0);
        if (i === 0) {
            gradient.addColorStop(0, 'rgba(26, 115, 232, 0.45)'); // Blue
            gradient.addColorStop(1, 'rgba(138, 63, 252, 0)');
        } else if (i === 1) {
            gradient.addColorStop(0, 'rgba(138, 63, 252, 0.45)'); // Purple
            gradient.addColorStop(1, 'rgba(209, 46, 255, 0)');
        } else if (i === 2) {
            gradient.addColorStop(0, 'rgba(209, 46, 255, 0.4)'); // Magenta
            gradient.addColorStop(1, 'rgba(255, 126, 41, 0)');
        } else {
            gradient.addColorStop(0, 'rgba(255, 126, 41, 0.35)'); // Orange
            gradient.addColorStop(1, 'rgba(26, 115, 232, 0)');
        }
        
        ctx.strokeStyle = gradient;
        ctx.lineWidth = i === 0 ? 2.5 : 1.5;
        
        const phaseShift = i * (Math.PI / 2) + wavePhase;
        const offsetHeight = height / 2;
        
        for (let x = 0; x < width; x++) {
            const angle = (x / width) * Math.PI * 2 * frequencyFactor + phaseShift;
            // Damping envelope to pinch the waves elegantly at the edges (premium aesthetic)
            const envelope = Math.sin((x / width) * Math.PI);
            const y = Math.sin(angle) * baseAmplitude * envelope + offsetHeight;
            
            if (x === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
    }
}
drawVisualizer();

// --- 7. CHAT LOG PANEL TOGGLER & INPUTS ---
toggleChatBtn.addEventListener('click', () => {
    chatDrawer.classList.toggle('collapsed');
    // Set focus on input field on expand
    if (!chatDrawer.classList.contains('collapsed')) {
        chatTextInput.focus();
    }
});

chatInputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatTextInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    // Add user message bubble
    const bubble = document.createElement('div');
    bubble.className = "chat-bubble user";
    bubble.textContent = text;
    chatHistory.appendChild(bubble);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // Send text payload to server WebSocket proxy
    ws.send(JSON.stringify({
        type: "text",
        text: text
    }));
    
    chatTextInput.value = "";
    updateVoiceState('THINKING');
});

// Sound feedback mute toggle
toggleMuteBtn.addEventListener('click', () => {
    isMuted = !isMuted;
    if (isMuted) {
        soundOnIcon.classList.add('hidden');
        soundOffIcon.classList.remove('hidden');
    } else {
        soundOnIcon.classList.remove('hidden');
        soundOffIcon.classList.add('hidden');
    }
});

// Microphone toggle
micBtn.addEventListener('click', async () => {
    if (state === 'IDLE') {
        updateVoiceState('LISTENING');
        await startMicrophone();
    } else {
        updateVoiceState('IDLE');
    }
});

// --- 8. TELEMETRY MONITORING & LIFECYCLE CONTROLS ---
async function pollSystemStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) return;
        
        const data = await response.json();
        
        // 1. On-Air feed metadata
        const camMap = {
            "cam_1": "CAM 1 - WIDE STUDIO",
            "cam_2": "CAM 2 - HOST CLOSE-UP",
            "pixel_11": "PIXEL 11 - MOBILE MOUNT"
        };
        onAirCameraTitle.textContent = camMap[data.camera_on_air] || data.camera_on_air.toUpperCase();
        onAirFrameDesc.textContent = data.web_page_frame;
        
        // PTZ coords
        const ptz = data.ptz_positions[data.camera_on_air] || { pan: 0.0, tilt: 0.0, zoom: 1.0 };
        telemetryPan.textContent = `${ptz.pan.toFixed(1)}°`;
        telemetryTilt.textContent = `${ptz.tilt.toFixed(1)}°`;
        telemetryZoom.textContent = `${ptz.zoom.toFixed(1)}x`;
        
        // 2. Audio Desk decibels
        const levels = data.audio_levels;
        const hostDb = levels.mic_host;
        const guestDb = levels.mic_guest;
        
        vuHostDb.textContent = `${hostDb.toFixed(1)} dB`;
        vuGuestDb.textContent = `${guestDb.toFixed(1)} dB`;
        
        // Normalize DB range [-60dB, -5dB] to CSS height percentage [5%, 100%]
        const normalizeDbToPct = (db) => {
            const clamped = Math.max(-60, Math.min(-5, db));
            const ratio = (clamped + 60) / 55; // 0.0 to 1.0
            return `${Math.floor(ratio * 95 + 5)}%`;
        };
        
        vuHostBar.style.height = normalizeDbToPct(hostDb);
        vuGuestBar.style.height = normalizeDbToPct(guestDb);
        
        // 3. Rundown updates
        // To prevent wiping active nodes, check if active segment changed
        const listItems = rundownList.querySelectorAll('.rundown-item');
        let currentActiveTitle = "";
        listItems.forEach(item => {
            if (item.classList.contains('active')) {
                currentActiveTitle = item.querySelector('.seg-title').textContent;
            }
        });
        
        if (currentActiveTitle !== data.active_segment) {
            // Re-render rundown list
            rundownList.innerHTML = "";
            const rundownSegments = [
                {"title": "Intro Bumper", "duration": "30s", "notes": "FOH starts, count down, play intro package."},
                {"title": "Welcome and Chat", "duration": "2m", "notes": "Host and Guest chat, camera transitions."},
                {"title": "Deep Dive & Tension", "duration": "2m", "notes": "Pick up tension, do close-ups using Pixel 11."},
                {"title": "Wrap-up & Outro", "duration": "30s", "notes": "Wrap up and cue outro graphics."}
            ];
            
            rundownSegments.forEach(seg => {
                const li = document.createElement('li');
                li.className = "rundown-item" + (seg.title === data.active_segment ? " active" : "");
                li.innerHTML = `
                    <span class="seg-bullet"></span>
                    <div class="seg-details">
                        <div class="seg-title">${seg.title}</div>
                        <div class="seg-notes">${seg.notes}</div>
                    </div>
                    <span class="seg-duration">${seg.duration}</span>
                `;
                rundownList.appendChild(li);
            });
        }
        
        // 4. Director Decision Log scrolling terminal
        const decisions = data.director_decision_log;
        if (decisions && decisions.length > 0) {
            let logText = "";
            decisions.forEach(dec => {
                logText += `[Director Decision] Cut to ${dec.target.toUpperCase()} because: ${dec.reason}\n`;
            });
            directorConsoleLog.textContent = logText;
            directorConsoleLog.scrollTop = directorConsoleLog.scrollHeight;
        } else {
            directorConsoleLog.textContent = data.live_production_active 
                ? "[Director Loop] Analysing audio/video preview..." 
                : "[System] Studio systems operational. Awaiting Show Start.";
        }
        
        // Update general status text
        if (data.live_production_active) {
            systemStatusBadge.textContent = "BROADCAST LIVE";
            systemStatusBadge.style.color = "#ef4444";
            systemStatusBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";
            systemStatusBadge.style.background = "rgba(239, 68, 68, 0.1)";
        } else {
            systemStatusBadge.textContent = ws && ws.readyState === WebSocket.OPEN ? "HOST CONNECTED" : "STANDBY";
            systemStatusBadge.style.color = "#c084fc";
            systemStatusBadge.style.borderColor = "rgba(138, 63, 252, 0.3)";
            systemStatusBadge.style.background = "rgba(138, 63, 252, 0.12)";
        }
        
    } catch (err) {
        console.error("Error polling system status:", err);
    }
}

// Start Show Trigger
startShowBtn.addEventListener('click', async () => {
    try {
        await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'start' })
        });
        console.log("Start show commanded.");
    } catch (err) {
        console.error("Start show click failed:", err);
    }
});

// Stop Show Trigger
stopShowBtn.addEventListener('click', async () => {
    try {
        await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'stop' })
        });
        console.log("Stop show commanded.");
    } catch (err) {
        console.error("Stop show click failed:", err);
    }
});

// --- 9. STARTUP & POOLING INITIALIZATIONS ---
window.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    statusInterval = setInterval(pollSystemStatus, 800); // Poll state every 800ms
    pollSystemStatus(); // Run initial status check
});

// Graceful cleanup
window.addEventListener('beforeunload', () => {
    if (statusInterval) clearInterval(statusInterval);
    stopMicrophone();
    if (ws) ws.close();
});
