import cv2, io
import re
import requests
from datetime import datetime, timezone
from dateutil.parser import isoparse
from PIL import Image
from logger import logger
from config import VALID_TAGS, STREAM_SSL_VERIFY


def fetch_program_start(playlist_url):
    """
    Fetch the HLS playlist and extract the first PROGRAM-DATE-TIME tag,
    parsing it into a datetime with proper timezone handling.
    """
    r = requests.get(playlist_url, timeout=10, verify=STREAM_SSL_VERIFY)
    logger.debug(f"Playlist content:\n{r.text}")
    for line in r.text.splitlines():
        if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            ts = line.split(":", 1)[1]
            try:
                # Use dateutil to parse various ISO formats including offsets without colon
                return isoparse(ts)
            except Exception:
                # Fallback: insert colon into timezone offset if missing (e.g. -0300 -> -03:00)
                m = re.match(r"^(.*)([+-]\d{2})(\d{2})$", ts)
                if m:
                    fixed_ts = f"{m.group(1)}{m.group(2)}:{m.group(3)}"
                    try:
                        return datetime.fromisoformat(fixed_ts)
                    except Exception as e:
                        logger.error(f"Failed to parse fixed timestamp {fixed_ts!r}: {e}")
            break
    logger.warning("No PROGRAM-DATE-TIME tag found in playlist")
    return None


def get_delta_timecode(program_start):
  now = datetime.now(timezone.utc)
  if program_start is None:
    return "00:00:00"
  delta = now - program_start
  total = int(delta.total_seconds())
  h, rem = divmod(total, 3600)
  m, s = divmod(rem, 60)
  return f"{h:02d}:{m:02d}:{s:02d}"


def validate_timecode_format(timecode_str: str) -> str:
    """
    Validate a timecode string in HH:MM:SS format (hours:minutes:seconds).
    Returns the same string if valid, otherwise logs an error and returns "00:00:00".
    """
    # Strip optional "timecode:" prefix if present
    if timecode_str.lower().startswith("timecode:"):
        # Remove the prefix up to the first colon and trim whitespace
        timecode_str = timecode_str.split(":", 1)[1].strip()
    # Match HH:MM:SS where HH is 1- or 2-digit, MM and SS are exactly two digits
    if not re.match(r"^\d{1,2}:\d{2}:\d{2}$", timecode_str):
        logger.error(f"Invalid timecode format: {timecode_str!r}")
        return "00:00:00"
    hours, minutes, seconds = timecode_str.split(":")
    try:
        h = int(hours)
        m = int(minutes)
        s = int(seconds)
        if h < 0 or m < 0 or m > 59 or s < 0 or s > 59:
            raise ValueError("Invalid time component")
    except Exception as e:
        logger.error(f"Invalid timecode values in {timecode_str!r}: {e}")
        return "00:00:00"
    return timecode_str


def process_tags(tags_str: str) -> list[str]:
    tags = [tag.strip() for tag in tags_str.split(",")]
    filteredTags = [t for t in tags if t in VALID_TAGS]
    return filteredTags


def build_log_entry(raw_line: str) -> list[dict]:
    """
    Parse a raw log line formatted as:
        "timecode | type | tags | content"
    and return a dict with:
      - date: Current date
      - timecode: timecode from the stream
      - type: the event type (e.g. "transcript", "visual")
      - tags: list of tag strings
      - content: the text content
    """
    # print(raw_line)
    entries = []
    for line in raw_line.splitlines():
        if not line.strip():
            continue
        # logger.info(f"building log for: {line}")
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4:
            logger.error(f"Invalid log format: {line!r}")
            continue
        timecode_str, event_type, tags_str, content = parts
        
        entry = {
            "timestamp": datetime.now(tz=timezone.utc),
            "timecode": validate_timecode_format(timecode_str),
            "type": event_type,
            "tags": process_tags(tags_str),
            "content": content,
        }
        entries.append(entry)
    return entries


def frame_to_jpeg_bytes(frame):
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG")
    return buffer.getvalue()


def log_ffmpeg_errors(proc):
    for line in proc.stderr:
        logger.error("FFMPEG:", line.decode(errors='ignore').strip())
