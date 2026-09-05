
import os
import json
import time
import requests

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai
from google.genai import types


# ============================================================
# Load Environment Variables
# ============================================================

load_dotenv()


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI()


# ============================================================
# Environment Variables & Validation
# ============================================================

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

SN_URL = os.getenv("SN_INSTANCE_URL", "").strip().rstrip("/")
SN_USERNAME = os.getenv("SN_USERNAME", "").strip()
SN_PASSWORD = os.getenv("SN_PASSWORD", "")

if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env file")

if not SN_URL:
    raise ValueError("SN_INSTANCE_URL is missing from .env file")

if not SN_USERNAME:
    raise ValueError("SN_USERNAME is missing from .env file")

if not SN_PASSWORD:
    raise ValueError("SN_PASSWORD is missing from .env file")


print("============================================================")
print("Environment configuration loaded")
print("============================================================")
print(f"ServiceNow URL      : {SN_URL}")
print(f"ServiceNow Username : {SN_USERNAME}")
print(f"ServiceNow Password : {'LOADED' if SN_PASSWORD else 'MISSING'}")
print("============================================================")


# ============================================================
# Gemini Client & Model
# ============================================================

client = genai.Client(api_key=GEMINI_KEY)

GEMINI_MODEL = "gemini-3.6-flash"


# ============================================================
# Load Knowledge Base
# ============================================================

try:
    with open("kb_articles.json", "r", encoding="utf-8") as f:
        kb_data = json.load(f)

except FileNotFoundError:
    raise FileNotFoundError("kb_articles.json was not found")


# ============================================================
# Processed Incidents Guard
# ============================================================

PROCESSED_INCIDENTS = set()


# ============================================================
# Incident Payload
# ============================================================

class IncidentPayload(BaseModel):
    incident_sys_id: str
    number: str
    short_description: str
    description: str | None = None
    priority: int


# ============================================================
# Gemini Decision
# ============================================================

def get_gemini_decision(short_desc: str, desc: str) -> dict:

    knowledge_base = json.dumps(
        kb_data.get("articles", kb_data),
        indent=2,
        ensure_ascii=False
    )

    prompt = f"""
You are an IT support classifier.

IMPORTANT:
You must rely ONLY on the knowledge articles provided below.
Do NOT use outside knowledge.
Do NOT invent troubleshooting steps.

Knowledge Articles:
{knowledge_base}

Incident Details:
- Short Description: {short_desc}
- Description: {desc or ''}

Rules:
1. If the issue is clearly covered by one of the knowledge articles:
   decision = "respond"
   Provide the exact relevant solution from the article in the "message" field.

2. If the issue might match an article but the information is too vague or missing an important detail:
   decision = "ask"
   Ask one clear and useful clarifying question in the "message" field.

3. If no knowledge article covers the issue:
   decision = "escalate"
   Explain briefly why the issue needs human support.

Return ONLY valid JSON.

The JSON must have exactly this structure:
{{
    "decision": "respond",
    "message": "string"
}}

The value of "decision" MUST be exactly one of:
- respond
- ask
- escalate
"""

    max_retries = 4
    retry_delays = [2, 5, 10, 20]

    for attempt in range(max_retries):

        try:
            print(
                f"--> Calling Gemini "
                f"(attempt {attempt + 1}/{max_retries})..."
            )

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            response_text = response.text

            if not response_text:
                raise ValueError("Gemini returned an empty response")

            result = json.loads(response_text)

            decision = result.get("decision")
            message = result.get("message")

            if decision not in ["respond", "ask", "escalate"]:
                raise ValueError(
                    f"Invalid Gemini decision: {decision}"
                )

            if not isinstance(message, str):
                raise ValueError(
                    "Gemini message is not a string"
                )

            print("--> Gemini decision received successfully")

            return {
                "decision": decision,
                "message": message
            }

        except Exception as e:

            error_text = str(e)

            print(f"--> Gemini error: {error_text}")

            temporary_error = any(
                code in error_text
                for code in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "INTERNAL",
                    "DEADLINE_EXCEEDED"
                ]
            )

            if temporary_error and attempt < max_retries - 1:

                delay = retry_delays[attempt]

                print(
                    f"--> Temporary Gemini error. "
                    f"Retrying in {delay} seconds..."
                )

                time.sleep(delay)

                continue

            print("--> Gemini request failed permanently")

            raise

    raise Exception(
        "Gemini request failed after all retries"
    )


# ============================================================
# Update ServiceNow Incident
# ============================================================

def update_servicenow_incident(
    sys_id: str,
    decision: str,
    message: str
):

    url = f"{SN_URL}/api/now/table/incident/{sys_id}"

    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # --------------------------------------------------------
    # Payload
    # --------------------------------------------------------

    if decision == "respond":

        payload = {
            "work_notes": message,
            "close_notes": message,
            "close_code": "Solved (Permanently)",
            "state": "6"
        }

    elif decision == "ask":

        payload = {
            "comments": message
        }

    elif decision == "escalate":

        payload = {
            "work_notes": (
                f"Escalated to human support: {message}"
            )
        }

    else:

        raise ValueError(
            f"Invalid decision: {decision}"
        )

    # --------------------------------------------------------
    # Send PATCH request
    # --------------------------------------------------------

    print("--> Updating ServiceNow incident...")
    print(f"--> ServiceNow URL: {url}")
    print(f"--> ServiceNow User: {SN_USERNAME}")

    try:

        response = requests.patch(
            url,
            auth=(SN_USERNAME, SN_PASSWORD),
            headers=headers,
            json=payload,
            timeout=15
        )

    except requests.RequestException as e:

        print(
            f"--> ServiceNow connection error: {e}"
        )

        raise

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    print(
        f"ServiceNow Update Status: "
        f"{response.status_code}"
    )

    print(
        f"ServiceNow Response: "
        f"{response.text}"
    )

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if response.status_code not in [200, 201]:

        raise Exception(
            "ServiceNow update failed with "
            f"status {response.status_code}"
        )

    print(
        "--> ServiceNow incident "
        "updated successfully"
    )


# ============================================================
# Process Incident
# ============================================================

def process_incident(payload: IncidentPayload):

    try:

        print(
            f"--> Processing {payload.number}..."
        )

        result = get_gemini_decision(
            payload.short_description,
            payload.description
        )

        decision = result.get("decision")
        message = result.get("message")

        print(
            f"--> Decision: {decision}"
        )

        print(
            f"--> Message: {message}"
        )

        update_servicenow_incident(
            payload.incident_sys_id,
            decision,
            message
        )

        print(
            f"--> Done updating {payload.number}"
        )

    except Exception as e:

        print(
            f"Error processing "
            f"{payload.number}: {e}"
        )


# ============================================================
# Webhook Endpoint
# ============================================================

@app.post(
    "/webhook",
    status_code=202
)
def webhook_endpoint(
    payload: IncidentPayload,
    background_tasks: BackgroundTasks
):

    if payload.incident_sys_id in PROCESSED_INCIDENTS:

        print(
            f"--> {payload.number} already processed"
        )

        return {
            "status": "already_processed"
        }

    PROCESSED_INCIDENTS.add(
        payload.incident_sys_id
    )

    background_tasks.add_task(
        process_incident,
        payload
    )

    print(
        f"--> {payload.number} accepted "
        "for processing"
    )

    return {
        "status": "accepted"
    }