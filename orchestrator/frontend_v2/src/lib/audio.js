let audioPlayerNode;
let audioPlayerContext;
let audioRecorderNode;
let audioRecorderContext;
let micStream;
let audioBuffer = [];
let bufferTimer = null;
let audioCallback;


function audioRecorderHandler(pcmData) {
  audioBuffer.push(new Uint8Array(pcmData));

  if (!bufferTimer) {
    bufferTimer = setInterval(sendBufferedAudio, 200); // 0.2 seconds
  }
}

function sendBufferedAudio() {
  if (audioBuffer.length === 0) {
    return;
  }

  let totalLength = 0;
  for (const chunk of audioBuffer) {
    totalLength += chunk.length;
  }

  const combinedBuffer = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of audioBuffer) {
    combinedBuffer.set(chunk, offset);
    offset += chunk.length;
  }

  if (audioCallback) {
    audioCallback(arrayBufferToBase64(combinedBuffer.buffer));
  }

  audioBuffer = [];
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function base64ToArray(base64) {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}


async function startAudioPlayerWorklet() {
  audioPlayerContext = new AudioContext({
    sampleRate: 24000,
  });

  await audioPlayerContext.audioWorklet.addModule('/pcm-player-processor.js');
  audioPlayerNode = new AudioWorkletNode(
    audioPlayerContext,
    'pcm-player-processor'
  );
  audioPlayerNode.connect(audioPlayerContext.destination);
}


async function startAudioRecorderWorklet(handler) {
  audioRecorderContext = new AudioContext({
    sampleRate: 16000
  });

  await audioRecorderContext.audioWorklet.addModule('/pcm-recorder-processor.js');

  micStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1
    },
  });

  const source = audioRecorderContext.createMediaStreamSource(micStream);
  audioRecorderNode = new AudioWorkletNode(
    audioRecorderContext,
    'pcm-recorder-processor'
  );

  source.connect(audioRecorderNode);
  audioRecorderNode.port.onmessage = (event) => {
    const pcmData = convertFloat32ToPCM(event.data);
    handler(pcmData);
  };
}

function convertFloat32ToPCM(inputData) {
  const pcm16 = new Int16Array(inputData.length);
  for (let i = 0; i < inputData.length; i++) {
    pcm16[i] = inputData[i] * 0x7fff;
  }
  return pcm16.buffer;
}

function initAudio(callback) {
  audioCallback = callback;
  startAudioPlayerWorklet();
  startAudioRecorderWorklet(audioRecorderHandler);
}

function stopAudioRecording() {
  if (bufferTimer) {
    clearInterval(bufferTimer);
    bufferTimer = null;
  }

  if (audioBuffer.length > 0) {
    sendBufferedAudio();
  }

  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
  }

  if (audioRecorderContext) {
    audioRecorderContext.close();
  }
}

function playAudio(audioData) {
  if (audioPlayerNode) {
    audioPlayerNode.port.postMessage(base64ToArray(audioData));
  }
}

function stopAudioPlayback() {
  if (audioPlayerNode) {
    audioPlayerNode.port.postMessage({
      command: 'endOfAudio'
    });
  }
}

export {
  initAudio,
  stopAudioRecording,
  playAudio,
  stopAudioPlayback
};
