# Cuez Rundown Agent
## Create & Activate Virtual Environment (Recommended):

```bash
python -m venv .venv
```
### macOS/Linux:

```bash
source .venv/bin/activate
```
### Windows CMD:
```bash
.venv\Scripts\activate.bat
```

### Windows PowerShell:
```bash
.venv\Scripts\Activate.ps1
```

## Install packages

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m cuez-rundown-agent
```

## Agent card

```bash
(.venv) ➜  cuez-rundown git:(cuez-rundown) ✗ curl -sS http://localhost:8001/.well-known/agent.json  | jq

{
  "capabilities": {
    "streaming": true
  },
  "defaultInputModes": [
    "text"
  ],
  "defaultOutputModes": [
    "text"
  ],
  "description": "Helps with the cuez rundown",
  "name": "Cuez Agent",
  "skills": [
    {
      "description": "Lists all episodes in the specified project.",
      "examples": [
        "list episodes in project"
      ],
      "id": "list_episodes",
      "name": "List episodes in a project",
      "tags": [
        "episode",
        "list"
      ]
    }
  ],
  "url": "http://0.0.0.0:8001/",
  "version": "1.0.0"
}
```

## Run A2A test
```bash
(.venv) ➜  cuez-rundown git:(cuez-rundown) ✗ python test_a2a.py     

Connecting to agent at http://localhost:8001...
Connection successful.
--- Single Turn Request ---
--- Single Turn Request Response ---
{"id":"a70a67ba-ecb5-4e6d-b168-5f46f51e7666","jsonrpc":"2.0","result":{"artifacts":[{"artifactId":"87414f27-8d26-484d-993e-db642ec4e1d2","parts":[{"kind":"text","text":"- Standard template"}]}],"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","history":[{"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","kind":"message","messageId":"6145541198634a0fafb8a17304a83c29","parts":[{"kind":"text","text":"List titles of all episodes"}],"role":"user","taskId":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef"},{"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","kind":"message","messageId":"86a32dff-2585-4945-815d-fe1318de5643","parts":[],"role":"agent","taskId":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef"}],"id":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef","kind":"task","status":{"state":"completed"}}}

---Query Task---
--- Query Task Response ---
{"id":"a34cda56-9bb4-4bbb-a667-fe231991ffa1","jsonrpc":"2.0","result":{"artifacts":[{"artifactId":"87414f27-8d26-484d-993e-db642ec4e1d2","parts":[{"kind":"text","text":"- Standard template"}]}],"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","history":[{"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","kind":"message","messageId":"6145541198634a0fafb8a17304a83c29","parts":[{"kind":"text","text":"List titles of all episodes"}],"role":"user","taskId":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef"},{"contextId":"a60fe2f6-7d7a-4fd3-a081-e0437fae92ec","kind":"message","messageId":"86a32dff-2585-4945-815d-fe1318de5643","parts":[],"role":"agent","taskId":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef"}],"id":"f5a25ca4-e3e6-4aae-84bf-0f814ffa27ef","kind":"task","status":{"state":"completed"}}}
```
