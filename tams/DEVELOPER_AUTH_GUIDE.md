# Developer Authentication Guide: Accessing the TAMS API

The Time Addressable Media Store (TAMS) API endpoint is secured using **Google Cloud IAM (Identity and Access Management)**. 

To make successful API requests (via scripts, cURL, or Postman), your requests must include a valid **Google ID Token** inside an `Authorization` HTTP header. 

This guide walks you through how to obtain this token and use it, even if you have never used Google Cloud before.

---

## 🔑 The Core Concept: How Authentication Works
Every HTTP request to the TAMS API must include this header:
```http
Authorization: Bearer <YOUR_GOOGLE_ID_TOKEN>
```
> ⚠️ **Important**: A Google **ID Token** is a JWT token containing your identity information. This is *different* from a standard Google *Access Token*. Make sure you generate an **ID Token**.

---

## 👤 Method A: For Human Developers (Local cURL, Postman, Python)

If you are a developer testing endpoints manually from your laptop, the easiest way to generate a token is by using the lightweight `gcloud` command-line utility.

### Step 1: Install the Google Cloud CLI
If you don't have it installed already:
- **Mac (Homebrew)**: `brew install --cask google-cloud-sdk`
- **Other OS**: Follow the 2-minute setup at [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

### Step 2: Sign In
Run this command in your terminal. It will open a browser window asking you to sign in with your corporate Google Account:
```bash
gcloud auth login
```

### Step 3: Set Your Active Project
Set the active project to the hackathon project:
```bash
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### Step 4: Generate Your ID Token
Run this command to print your current ID Token:
```bash
gcloud auth print-identity-token
```
*Output example:*
`eyJhbGciOiJSUzI1NiIsImtpZCI6IjFhMm...`

### Step 5: Make Your API Requests
Copy the token string from Step 4 and use it in your API tool:

#### 1. In cURL:
```bash
curl -X GET "https://tams-api-xxxxx-ew.a.run.app/sources" \
  -H "Authorization: Bearer <PASTE_YOUR_ID_TOKEN_HERE>"
```

#### 2. In Postman:
1. Go to the **Authorization** tab of your request.
2. Select **Type**: `Bearer Token`.
3. Paste the generated token into the **Token** field.

> 💡 **Tip**: ID Tokens expire after **1 hour**. If you get a `401 Unauthorized` or `403 Forbidden` error, simply rerun `gcloud auth print-identity-token` to get a fresh one.

---

## 🤖 Method B: For Programmatic Scripts (Python, Node, Go, .NET)

If you are running automated ingestion/outgestion scripts, you should use a **Service Account** instead of a personal Google login.

### Step 1: Request a Service Account Key
Ask your project administrator for a **TAMS Service Account JSON Key File**. This file looks like this:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "xxxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "tams-api-sa@your-project.iam.gserviceaccount.com"
}
```

### Step 2: Set Your Environment Variable
Save that JSON key file securely on your server/laptop (do *never* commit it to git) and define this environment variable in your terminal:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### Step 3: Let SDKs Handle Authentication (Automatic)
The official Google Cloud client libraries will automatically detect this environment variable and handle authentication, token generation, and token refresh automatically behind the scenes.

#### Example (Python):
```python
import os
import requests
import google.auth
import google.auth.transport.requests

# 1. Fetch credentials automatically from GOOGLE_APPLICATION_CREDENTIALS
credentials, project_id = google.auth.default()

# 2. Define the Cloud Run Service URL as the audience
tams_api_url = "https://tams-api-xxxxx-ew.a.run.app"

# 3. Generate a fresh ID Token
auth_request = google.auth.transport.requests.Request()
credentials.refresh(auth_request)
id_token = credentials.token

# 4. Invoke TAMS
headers = {"Authorization": f"Bearer {id_token}"}
response = requests.get(f"{tams_api_url}/sources", headers=headers)
print(response.json())
```

---

## 🔍 Troubleshooting & Common Errors

#### 🔴 Error: `401 Unauthorized` or `403 Forbidden`
* **Cause 1**: Your ID Token has expired (tokens are only valid for 60 minutes). Rerun the generator step.
* **Cause 2**: You used an *Access Token* instead of an *ID Token*. 
  * ❌ *Incorrect command*: `gcloud auth print-access-token`
  *  *Correct command*: `gcloud auth print-identity-token`
* **Cause 3**: Your Google account or Service Account hasn't been granted the role `Cloud Run Invoker` (`roles/run.invoker`) on the `tams-api` service. Contact your GCP Project Owner.
