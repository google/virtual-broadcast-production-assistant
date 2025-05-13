# -*- coding: utf-8 -*-
"""
Analyzes a video stream (Webcam, File, or HLS) using Vertex AI Gemini streaming API,
incorporating both video frames and audio chunks. Logs results with simulated
timecode in JSON format.

Prerequisites:
1. Google Cloud Project with Vertex AI API enabled.
2. Authentication configured (e.g., `gcloud auth application-default login`).
3. Python libraries installed:
   pip install google-cloud-aiplatform opencv-python Pillow ffmpeg-python
4. OpenCV installed with FFmpeg support.
5. FFmpeg executable installed and accessible in the system PATH.
"""
import base64
import cv2  # OpenCV for video capture
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
import time
import datetime
import json
from os import environ
import io  # Required for sending image/audio data
from PIL import Image  # For image handling if needed
import ffmpeg  # For audio capture
import threading  # For running audio capture in background
import queue  # For passing audio data between threads
import subprocess  # To run ffmpeg process
import struct  # For creating WAV header

# --- Configuration ---
PROJECT_ID = environ.get("PROJECT_ID",
                         "your-gcp-project-id")  # Replace with your Project ID
LOCATION = "us-central1"  # Replace with your Vertex AI Location
# Reverted model name for debugging data format issues
MODEL_NAME = "gemini-2.0-flash"  # Or gemini-1.5-pro-001

# --- Video/Audio Source ---
# Choose ONE source type by uncommenting the desired SOURCE line
# and commenting out the others. Ensure it contains both video and audio.

# Option 1: HLS Stream URL
SOURCE_URL = "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8"  # <--- REPLACE with your actual HLS stream URL

# Option 2: Video File Path (with audio)
# SOURCE_URL = "path/to/your/video_with_audio.mp4"

# Note: Webcam (e.g., 0) typically requires separate handling for audio capture
# not covered by this ffmpeg stream approach. Use HLS or File for this script.

# --- Analysis Configuration ---
ANALYSIS_PROMPT = """
Act as a commentator for this media feed, considering BOTH the video frames AND the accompanying audio.
Describe what is happening visually and audibly.
Reference previous events or context from earlier in the feed when relevant.
Provide a concise, flowing commentary rather than a static description of just the current moment.
Focus on actions, sounds, speech, changes, and the overall narrative unfolding.
"""
SECONDS_PER_REQUEST = 2.0  # Analyze roughly every 2 seconds
AUDIO_CHUNK_DURATION = 2.0  # Duration of audio to send with each request (seconds)
OUTPUT_JSON_FILE = "video_audio_analysis_log.json"
AUDIO_SAMPLE_RATE = 16000  # Sample rate for audio capture (Hz)
AUDIO_CHANNELS = 1  # Mono audio
AUDIO_BIT_DEPTH = 16  # Bits per sample

# --- Global Queue for Audio Data ---
audio_queue = queue.Queue(maxsize=10)  # Buffer for audio chunks (bytes)

# --- Helper Functions ---


def timestamp_to_timecode(frame_number, frame_rate):
  """Converts a frame number to HH:MM:SS:FF timecode string."""
  if frame_rate <= 0:
    print("Warning: Invalid frame rate (<=0). Using 00:00:00:00.")
    return "00:00:00:00"
  total_seconds = frame_number / frame_rate
  hours = int(total_seconds // 3600)
  minutes = int((total_seconds % 3600) // 60)
  seconds = int(total_seconds % 60)
  frames = int(frame_number % frame_rate)
  return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def frame_to_base64(frame):
  """Encodes an OpenCV frame (numpy array) to base64 JPEG."""
  pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
  buffer = io.BytesIO()
  pil_img.save(buffer, format="JPEG")
  return base64.b64encode(buffer.getvalue()).decode("utf-8")


def add_wav_header(audio_data,
                   sample_rate=AUDIO_SAMPLE_RATE,
                   channels=AUDIO_CHANNELS,
                   bit_depth=AUDIO_BIT_DEPTH):
  """Adds a standard WAV header to raw PCM audio data."""
  datasize = len(audio_data)
  o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
  o += struct.pack(
      '<I', datasize +
      36)  # (4byte) File size (doesn't include RIFF identifier or file size)
  o += bytes("WAVE", 'ascii')  # (4byte) File type
  o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
  o += struct.pack('<I', 16)  # (4byte) Length of above format data
  o += struct.pack('<H', 1)  # (2byte) Format type (1 - PCM)
  o += struct.pack('<H', channels)  # (2byte) Number of Channels
  o += struct.pack('<I', sample_rate)  # (4byte) Sample Rate
  o += struct.pack('<I', sample_rate * channels *
                   (bit_depth // 8))  # (4byte) Byte Rate
  o += struct.pack(
      '<H', channels *
      (bit_depth // 8))  # (2byte) Block Align bytes per sample * channels
  o += struct.pack('<H', bit_depth)  # (2byte) Bits per sample
  o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
  o += struct.pack('<I', datasize)  # (4byte) Data size in bytes
  return o + audio_data


# --- Audio Capture Thread ---


def capture_audio(stream_url, stop_event):
  """
  Continuously captures audio from the stream using FFmpeg
  and puts chunks into the global audio_queue.
  Runs in a separate thread.
  """
  print("Starting audio capture thread...")
  try:
    process = (
        ffmpeg.input(stream_url, thread_queue_size=1024)
        # Ensure ffmpeg output matches header parameters
        .output('pipe:',
                format='s16le',
                acodec='pcm_s16le',
                ar=AUDIO_SAMPLE_RATE,
                ac=AUDIO_CHANNELS).global_args(
                    '-hide_banner', '-loglevel',
                    'error').run_async(pipe_stdout=True))

    bytes_per_sample = AUDIO_BIT_DEPTH // 8
    bytes_per_second = AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * bytes_per_sample
    chunk_size = int(bytes_per_second * AUDIO_CHUNK_DURATION)
    print(
        f"Audio capture: Reading chunks of {chunk_size} bytes ({AUDIO_CHUNK_DURATION}s)"
    )

    while not stop_event.is_set():
      in_bytes = process.stdout.read(chunk_size)
      if not in_bytes:
        print("Audio stream ended or error reading audio.")
        break

      if len(in_bytes) < chunk_size:
        print(
            f"Warning: Read partial audio chunk ({len(in_bytes)} / {chunk_size} bytes). Skipping this chunk."
        )
        continue  # Skip potentially incomplete chunks, especially at the end

      try:
        audio_queue.put(in_bytes, block=False)
      except queue.Full:
        try:
          audio_queue.get_nowait()
          audio_queue.put(in_bytes, block=False)
        except queue.Empty:
          pass
        except queue.Full:
          print("Audio queue still full, dropping chunk.")

    print("Audio capture thread stopping...")
    process.stdout.close()
    # Terminate process if it doesn't exit cleanly after stdout close
    try:
      process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
      print("FFmpeg process did not exit cleanly, terminating.")
      process.terminate()
      process.wait()
    print("Audio capture process finished.")

  except Exception as e:
    print(f"Error in audio capture thread: {e}")


# --- Main Analysis Function ---


def analyze_video_stream():
  """Captures video/audio, sends data to Gemini, logs analysis with timecode."""

  print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
  vertexai.init(project=PROJECT_ID, location=LOCATION)

  print(f"Loading model: {MODEL_NAME}")
  model = GenerativeModel(MODEL_NAME)

  print(f"Attempting to open video source: {SOURCE_URL}")
  cap = cv2.VideoCapture(SOURCE_URL)

  if not cap.isOpened():
    print(f"Error: Could not open video source '{SOURCE_URL}'.")
    return

  frame_rate = cap.get(cv2.CAP_PROP_FPS)
  print(f"Reported Video Frame Rate: {frame_rate:.2f} fps")
  if frame_rate <= 0:
    print(
        "Warning: Frame rate not accurately reported. Using default 30fps for timecode."
    )
    frame_rate = 30

  stop_audio_event = threading.Event()
  audio_thread = threading.Thread(target=capture_audio,
                                  args=(SOURCE_URL, stop_audio_event),
                                  daemon=True)
  audio_thread.start()
  print("Waiting for audio thread to initialize...")
  time.sleep(3)  # Increased wait time slightly

  frame_count = 0
  analysis_log = []
  last_request_time = time.time()

  print("Starting video/audio analysis loop (Press Ctrl+C to quit)...")

  try:
    while True:
      ret, frame = cap.read()
      if not ret:
        print(
            "Warning: Could not read video frame. Stream might have ended or stalled."
        )
        time.sleep(1)
        if not cap.isOpened():
          print("Video source closed.")
          break
        continue

      current_time = time.time()
      frame_count += 1
      timecode = timestamp_to_timecode(frame_count, frame_rate)

      if current_time - last_request_time >= SECONDS_PER_REQUEST:
        last_request_time = current_time

        # Get the latest audio chunk
        latest_audio_chunk_raw = None
        while not audio_queue.empty():
          try:
            latest_audio_chunk_raw = audio_queue.get_nowait()
          except queue.Empty:
            break

        # --- Debugging Print ---
        print(
            f"Attempting analysis at frame {frame_count} (Timecode: {timecode})..."
        )
        if frame is None:
          print("  -> Video frame is missing!")
        if latest_audio_chunk_raw is None:
          print("  -> Audio chunk is missing!")
        # --- End Debugging Print ---

        if frame is not None and latest_audio_chunk_raw is not None:
          print(
              f"  -> Got video frame and audio chunk (raw size: {len(latest_audio_chunk_raw)} bytes)"
          )
          frame_b64 = frame_to_base64(frame)

          # --- Add WAV Header ---
          audio_with_header = add_wav_header(latest_audio_chunk_raw)
          print(f"  -> Audio with header size: {len(audio_with_header)} bytes")

          request_payload = [
              Part.from_data(mime_type="image/jpeg",
                             data=base64.b64decode(frame_b64)),
              # Send audio with header
              Part.from_data(
                  mime_type="audio/wav",  # Explicitly state WAV
                  data=audio_with_header),
              ANALYSIS_PROMPT,
          ]

          try:
            response = model.generate_content(
                request_payload,
                generation_config={"temperature": 0.3},
                safety_settings={
                    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH:
                    generative_models.HarmBlockThreshold.
                    BLOCK_MEDIUM_AND_ABOVE,
                    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
                    generative_models.HarmBlockThreshold.
                    BLOCK_MEDIUM_AND_ABOVE,
                    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:
                    generative_models.HarmBlockThreshold.
                    BLOCK_MEDIUM_AND_ABOVE,
                    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT:
                    generative_models.HarmBlockThreshold.
                    BLOCK_MEDIUM_AND_ABOVE,
                })

            if response.candidates and response.candidates[0].content.parts:
              analysis_text = response.candidates[0].content.parts[0].text
              print(f"  Commentary: {analysis_text[:100]}...")
            # Handle cases where the response might be blocked or empty
            elif response.candidates and response.candidates[
                0].finish_reason != FinishReason.STOP:
              analysis_text = f"Analysis stopped: {response.candidates[0].finish_reason.name}"
              print(f"  {analysis_text}")
            else:
              analysis_text = "No commentary received (Empty response)."
              print(f"  {analysis_text}")

            log_entry = {
                "frame":
                frame_count,
                "timecode":
                timecode,
                "timestamp_unix":
                current_time,
                "analysis":
                analysis_text,
                "finish_reason":
                response.candidates[0].finish_reason.name
                if response.candidates else "N/A",
            }
            analysis_log.append(log_entry)

          except Exception as e:
            # Catch potential API errors more specifically if possible
            print(f"Error during Gemini API call: {e}")
            # Log more details about the error if available (e.g., e.response)
            log_entry = {
                "frame": frame_count,
                "timecode": timecode,
                "timestamp_unix": current_time,
                "analysis": f"API Error: {e}",
                "finish_reason": "ERROR",
            }
            analysis_log.append(log_entry)

        else:
          # This log message will now follow the debug prints above
          print(
              f"Skipping analysis at frame {frame_count}: Missing video frame or audio chunk."
          )
          log_entry = {
              "frame": frame_count,
              "timecode": timecode,
              "timestamp_unix": current_time,
              "analysis": "Skipped - missing frame or audio",
              "finish_reason": "SKIPPED",
          }
          analysis_log.append(log_entry)

      time.sleep(0.01)

  except KeyboardInterrupt:
    print("\nAnalysis stopped by user.")
  finally:
    print("Signalling audio thread to stop...")
    stop_audio_event.set()
    print("Releasing video capture...")
    cap.release()
    cv2.destroyAllWindows()
    print("Waiting for audio thread to join...")
    audio_thread.join(timeout=5.0)
    if audio_thread.is_alive():
      print("Warning: Audio thread did not exit cleanly.")

    if analysis_log:
      print(f"\nSaving analysis log to {OUTPUT_JSON_FILE}...")
      try:
        with open(OUTPUT_JSON_FILE, 'w') as f:
          json.dump(analysis_log, f, indent=2)
        print("Log saved successfully.")
      except IOError as e:
        print(f"Error saving log file: {e}")
    else:
      print("No analysis data was logged.")


# --- Run the Analysis ---
if __name__ == "__main__":
  # Check for placeholder values before running
  project_id_ok = PROJECT_ID != "your-gcp-project-id"
  source_url_ok = SOURCE_URL not in [
      "your_hls_stream_url.m3u8", "path/to/your/video_with_audio.mp4"
  ]

  if not project_id_ok:
    print(
        "Error: Please replace 'your-gcp-project-id' with your actual Google Cloud Project ID (or set the PROJECT_ID environment variable)."
    )
  if not source_url_ok:
    print(
        "Error: Please replace the placeholder SOURCE_URL with your actual HLS stream URL or file path in the script."
    )

  if project_id_ok and source_url_ok:
    analyze_video_stream()
  else:
    print("Exiting due to configuration errors.")
