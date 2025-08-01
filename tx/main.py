import sys
import uuid
import argparse
import warnings
import asyncio
# Make sure to load all env vars before start procesing
import config as config

from src.processor import (
    start_agent_session,
    process_agent_events,
    stream_to_agent,
)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

async def main():
    parser = argparse.ArgumentParser(description="Run the live stream processor.")
    parser.add_argument(
        "--stream-url", "-u",
        help="URL of the HLS stream (e.g. http://localhost:8888/stream.m3u8)"
    )
    parser.add_argument(
        "--user-id", "-i",
        help="Identifier for the agent session"
    )
    args = parser.parse_args()

    if not args.stream_url:
        print("Error: --stream-url is required", file=sys.stderr)
        sys.exit(1)

    user_id = args.user_id if args.user_id else str(uuid.uuid4())

    # Start the agent session
    live_events, live_request_queue = await start_agent_session(user_id)
    
    # Start tasks: printing agent events and processing stream
    printer_task = asyncio.create_task(process_agent_events(live_events))
    stream_task = asyncio.create_task(stream_to_agent(live_request_queue, args.stream_url))
    tasks = [printer_task, stream_task]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        for t in tasks:
            t.cancel()
        live_request_queue.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Service stoped")
    
