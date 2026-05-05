import asyncio
import config
import ffmpeg, cv2
import threading, time, queue, subprocess
from config import GEMINI_MODEL_FOR_AGENT
from logger import logger
from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.agents import Agent
from google.genai.types import Blob, Part, Content
from src.prompts import ROOT_PROMPT, INSTRUCTIONS
from src.embeddings import generate_embeddings_for_index
from src.firestore_repo import FirestoreRepo
from src.utils import (
    fetch_program_start,
    get_delta_timecode,
    build_log_entry,
    frame_to_jpeg_bytes,
    log_ffmpeg_errors,
)

firestoreDB = FirestoreRepo(config.DB_COLLECTION_NAME)
audio_queue = queue.Queue(maxsize=10)

async def start_agent_session(user_id: str):
    """Starts an agent session"""

    root_agent = Agent(
      name="live_cast_analyst_agent",
      model=GEMINI_MODEL_FOR_AGENT,
      description=ROOT_PROMPT,
      instruction=INSTRUCTIONS,
    )

    runner = InMemoryRunner(
        app_name=config.APP_NAME,
        agent=root_agent,
    )

    session = await runner.session_service.create_session(
        app_name=config.APP_NAME,
        user_id=user_id,
    )

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(
        user_id=user_id,
        session_id=session.id,
        live_request_queue=live_request_queue,
        run_config=RunConfig(response_modalities=["TEXT"]),
    )
    return live_events, live_request_queue


async def process_agent_events(live_events):
    """Processes agent responses"""
    buffer = []
    async for event in live_events:
        if event.turn_complete or event.interrupted:
            full_text = "".join(buffer).strip()
            buffer.clear()
            # Skip if there's nothing to process
            if not full_text:
                continue
            
            # Build entries and skip if empty
            entries = build_log_entry(full_text)
            if not entries:
                continue
            
            # Store entries and their embeddings
            embeddings = generate_embeddings_for_index(entries)
            firestoreDB.batch_add(entries, embeddings)
            continue

        part: Part = (event.content and event.content.parts and event.content.parts[0])
        if not part:
          logger.error("Not a part")
          continue

        if not part.text:
          mime = part.inline_data.mime_type if part.inline_data else 'unknown'
          logger.error(f"Invalid part type: expected text, got {mime}")
          continue

        if part.text and event.partial:
          buffer.append(part.text)
          continue


def capture_audio(stream_url: str, stop_event):
  """
  Continuously captures audio from the stream using FFmpeg
  and puts chunks into the global audio_queue.
  Runs in a separate thread.
  """
  logger.info("Starting audio capture thread...")
  try:
    process = (
        ffmpeg
        .input(stream_url, thread_queue_size=1024)
        .output(
          'pipe:',
          format='s16le',
          acodec='pcm_s16le',
          ar=config.AUDIO_SAMPLE_RATE,
          ac=config.AUDIO_CHANNELS,
          vn=None, # disable video
        )
        .global_args(
          '-protocol_whitelist',
          'file,http,https,tcp,tls',
          '-safe',
          '0',
          '-hide_banner',
          '-loglevel',
          'error',
        )
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )

    threading.Thread(target=log_ffmpeg_errors, args=(process,), daemon=True).start()

    bytes_per_sample = config.AUDIO_BIT_DEPTH // 8
    bytes_per_second = config.AUDIO_SAMPLE_RATE * config.AUDIO_CHANNELS * bytes_per_sample
    chunk_size = int(bytes_per_second * config.AUDIO_CHUNK_DURATION)

    logger.info(f"Audio capture: Reading chunks of {chunk_size} bytes ({config.AUDIO_CHUNK_DURATION}s)")

    while not stop_event.is_set():
      in_bytes = process.stdout.read(chunk_size)
      logger.debug(f"Read {len(in_bytes) if in_bytes else 0} bytes")
      if not in_bytes:
        logger.error("Audio stream ended or error reading audio.")
        break

      if len(in_bytes) < chunk_size:
        logger.warning(f"Read partial audio chunk ({len(in_bytes)} / {chunk_size} bytes). Skipping this chunk.")
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
          logger.error("Audio queue still full, dropping chunk.")

    logger.info("Audio capture thread stopping...")
    process.stdout.close()
    # Terminate process if it doesn't exit cleanly after stdout close
    try:
      process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
      logger.error("FFmpeg process did not exit cleanly, terminating.")
      process.terminate()
      process.wait()
    logger.info("Audio capture process finished.")

  except Exception as e:
    logger.error(f"Error in audio capture thread: {e}")


def analyze_video_stream(stream_url: str, live_request_queue):
  """Captures video/audio, sends data to Gemini, logs analysis with timecode."""

  logger.info(f"Attempting to open video source: {stream_url}")
  cap = cv2.VideoCapture(stream_url)

  if not cap.isOpened():
    logger.error(f"Could not open video source '{stream_url}'.")
    return

  frame_rate = cap.get(cv2.CAP_PROP_FPS)
  logger.info(f"Reported Video Frame Rate: {frame_rate:.2f} fps")
  if frame_rate <= 0:
    logger.warning("Frame rate not accurately reported. Using default 30fps for timecode.")
    frame_rate = 30

  stop_audio_event = threading.Event()
  audio_thread = threading.Thread(
    target=capture_audio,
    args=(stream_url, stop_audio_event),
    daemon=True
  )
  audio_thread.start()
  logger.info("Waiting for audio thread to initialize...")
  time.sleep(3)

  frame_count = 0
  last_request_time = time.time()
  program_start = fetch_program_start(stream_url)

  logger.info("Starting video and audio analysis")
  try:
    while True:
      ret, frame = cap.read()
      if not ret:
        logger.warning("Could not read video frame. Stream might have ended or stalled.")
        time.sleep(1)
        if not cap.isOpened():
          logger.info("Video source closed.")
          break
        continue

      current_time = time.time()
      frame_count += 1

      if current_time - last_request_time >= config.SECONDS_PER_REQUEST:
        last_request_time = current_time

        try:
          latest_audio_chunk_raw = audio_queue.get(timeout=config.AUDIO_CHUNK_DURATION)
        except queue.Empty:
          logger.info("Timeout waiting audio; skipping this loop")
          latest_audio_chunk_raw = None

        logger.debug(f"Attempting analysis at frame {frame_count}")
        if frame is None:
          logger.warning("Video frame is missing!")
        if latest_audio_chunk_raw is None:
          logger.warning("Audio chunk is missing!")


        if frame is not None and latest_audio_chunk_raw is not None:
          logger.debug(f"Got video frame and audio chunk (raw size: {len(latest_audio_chunk_raw)} bytes)")
          jpeg_bytes = frame_to_jpeg_bytes(frame)

          tc = get_delta_timecode(program_start)
          logger.debug(f"Delta timecode is: {tc}")
          live_request_queue.send_realtime(Blob(mime_type="image/jpeg", data=jpeg_bytes))
          live_request_queue.send_realtime(Blob(mime_type="audio/pcm;rate=16000", data=latest_audio_chunk_raw))
          content = Content(role="user", parts=[Part.from_text(text=f"timecode: {tc}")])
          live_request_queue.send_content(content=content)
          
        else:
          # This log message will now follow the debug prints above
          logger.info(f"Skipping analysis at frame {frame_count}: Missing video frame or audio chunk.")

      time.sleep(0.01)

  except KeyboardInterrupt:
    logger.info("\nAnalysis stopped by user.")
  finally:
    logger.info("Signalling audio thread to stop...")
    stop_audio_event.set()
    logger.info("Releasing video capture...")
    cap.release()
    cv2.destroyAllWindows()
    logger.warning("Waiting for audio thread to join...")
    audio_thread.join(timeout=5.0)
    if audio_thread.is_alive():
      logger.warning("Audio thread did not exit cleanly.")


async def stream_to_agent(live_request_queue, url):
    """STREAM to agent communication"""
    await asyncio.to_thread(analyze_video_stream, url, live_request_queue)
