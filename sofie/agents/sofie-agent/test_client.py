import asyncio
import sys
import httpx
import uuid
from a2a.client import A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <message>")
        return

    agent_url = "http://127.0.0.1:8001"
    message = sys.argv[1]

    async with httpx.AsyncClient() as httpx_client:
        try:
            client = await A2AClient.get_client_from_agent_card_url(
                httpx_client, agent_url
            )
        except Exception as e:
            print(f"Failed to initialize A2AClient: {e}")
            return

        send_message_payload = MessageSendParams(
            message={
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"text": message}],
            }
        )
        send_request = SendMessageRequest(params=send_message_payload)
        
        try:
            response = await client.send_message(send_request)
            print("Agent response:", response)
        except Exception as e:
            print(f"Error sending message: {e}")

if __name__ == "__main__":
    asyncio.run(main())