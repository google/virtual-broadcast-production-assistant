"""
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """

import requests
from termcolor import colored
from fastapi import FastAPI, HTTPException

from payloads.cuez_message import CuezRequest, CuezResponse
from config import LocalSettings

app = FastAPI(title="Chat API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    app.local_settings = LocalSettings()
    print(colored(f"ENV VARS=\n{app.local_settings}", 'yellow'))
    print(colored(f"cuez-custom-proxy is initialised", "yellow"))

@app.post("/cuez-proxy")
async def chat(payload: CuezRequest) -> CuezResponse:

    print('/cuez-proxy method hit')
    print(f'/cuez-proxy method hit - payload is {payload}')
    try:
        # Get host and port from local settings
        host = app.local_settings.CUEZ_API_HOST
        port = app.local_settings.CUEZ_API_PORT
        username = app.local_settings.CUEZ_USERNAME
        password = app.local_settings.CUEZ_PASSWORD

        # Construct downstream API URL
        cuez_api_url = f"http://{host}:{port}/api/{payload.path}"

        # Prepare authentication if host is on ngrok-free.app
        auth = None
        if ".ngrok-free.app" in host:
            cuez_api_url = f"https://{host}/api/{payload.path}"
            auth = (username, password)
            print(f'Using Auth {auth}')

        print(f'Making API request to Cuez with {cuez_api_url}')

        # Make the downstream API call, including authentication if needed
        cuez_response = requests.get(cuez_api_url, auth=auth, timeout=120)
        cuez_response.raise_for_status()
        cuez_response = cuez_response.json()
        print(type(cuez_response))
        print(f"Downstream API response: {cuez_response}")

        response = CuezResponse(response=cuez_response)

    except requests.RequestException as e:
        print(f"Error communicating with downstream API: {e}")
        raise HTTPException(status_code=502, detail="Bad Gateway") from e
    except HTTPException as e:
            print(f"HTTPException: {e.detail}")
            raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}") from e

    return response
