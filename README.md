# SprintsAI-Task0-
Agentic Incident Flow on Your PDI

# ServiceNow AI Incident Support with Gemini

## Project Overview

This project connects ServiceNow with Google Gemini to handle support tickets automatically.

When a new incident is created in ServiceNow, the incident details are sent to a FastAPI application. The application sends the issue to Google Gemini, which checks the local knowledge base.

Based on the knowledge articles, Gemini decides what action should be taken and the application updates the incident in ServiceNow.

## Prerequisites

Before you start, make sure you have:

* **Python 3.11 or newer**
* A **ServiceNow Developer Instance (PDI)**
* A **Google Gemini API Key**

You can check your Python version with:

```bash
python --version
```

## Project Structure

The project contains the following files:

```text
├── main.py              # Main FastAPI application
├── kb_articles.json     # Knowledge base articles
├── requirements.txt     # Required Python packages
├── .env                 # Environment variables and credentials
└── README.md            # Project documentation
```

## Installation

Follow these steps to set up the project.

### 1. Open the Project Folder

Open your terminal or command prompt and go to the project folder:

```bash
cd path/to/your/project-folder
```

Replace `path/to/your/project-folder` with the actual path of your project.

### 2. Create a Virtual Environment

A virtual environment keeps the project packages separate from other Python projects.

On Windows:

```bash
python -m venv venv
```

On Mac/Linux:

```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment

On Windows:

```bash
venv\Scripts\activate
```

On Mac/Linux:

```bash
source venv/bin/activate
```

### 4. Install the Required Packages

Install all required packages using:

```bash
pip install -r requirements.txt
```

## Environment Variables

A `.env` file is provided in the project folder.

Open the `.env` file and replace the placeholder values with your own information.

The file should contain:

```env
GEMINI_API_KEY=your_gemini_api_key
SN_INSTANCE_URL=https://your-instance.service-now.com
SN_USERNAME=your_username
SN_PASSWORD=your_password
```

### Environment Variables Explanation

| Variable          | Description                          |
| ----------------- | ------------------------------------ |
| `GEMINI_API_KEY`  | Your Google Gemini API key.          |
| `SN_INSTANCE_URL` | The URL of your ServiceNow instance. |
| `SN_USERNAME`     | Your ServiceNow username.            |
| `SN_PASSWORD`     | Your ServiceNow password.            |

Make sure to replace the example values with your own credentials.

**Important:** Never share your real password or API key. Do not upload the `.env` file to GitHub.

## Knowledge Base

The project uses a file called `kb_articles.json`.

This file contains the knowledge articles that Gemini uses to understand and solve incidents.

The file should be in the same folder as `main.py`:

```text
project-folder/
├── main.py
└── kb_articles.json
```

Gemini uses only the articles in this file when deciding how to handle an incident.

## Running the Project

After installing the requirements and configuring the `.env` file, start the FastAPI application with:

```bash
uvicorn main:app --reload
```

The application will run locally at:

```text
http://127.0.0.1:8000
```

You can also open the FastAPI documentation at:

```text
http://127.0.0.1:8000/docs
```

If the application starts correctly, you should see a message similar to:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

## Webhook

The application has a webhook endpoint:

```text
POST /webhook
```

A webhook is an endpoint that receives data from another system.

In this project, ServiceNow sends incident information to the FastAPI application using a `POST` request.

The complete URL during local testing is:

```text
http://127.0.0.1:8000/webhook
```

### Expected Payload

The webhook expects incident data in JSON format:

```json
{
  "incident_sys_id": "9d3850cd97112110c14b5666f053af66",
  "number": "INC0010001",
  "short_description": "Printer not printing after office move",
  "description": "It was working yesterday. I tried turning it off and on.",
  "priority": 3
}
```

## ServiceNow Setup

ServiceNow needs to send the incident information to the FastAPI webhook.

A **Business Rule** can be used to trigger this process automatically when an incident is created or updated.

The basic flow is:

```text
ServiceNow Incident
        ↓
Business Rule
        ↓
POST /webhook
        ↓
FastAPI
```

The Business Rule collects the required incident information and sends it to the webhook.

When the application is running locally, ServiceNow cannot directly access:

```text
http://127.0.0.1:8000
```

In this case, a tunneling tool such as **ngrok** can be used to provide a public URL that points to the local FastAPI application.

The webhook URL in ServiceNow should then use the public URL provided by the tunneling tool.

## How the AI Process Works

Each incident follows these steps:

### 1. Incident Created

A new incident is created in ServiceNow.

### 2. ServiceNow Sends the Incident

The Business Rule sends the incident information to:

```text
POST /webhook
```

### 3. FastAPI Receives the Incident

FastAPI receives the incident data and starts processing it.

### 4. Gemini Analyzes the Incident

FastAPI sends the incident's short description and description to Google Gemini.

### 5. Gemini Checks the Knowledge Base

Gemini checks `kb_articles.json` to find a matching knowledge article.

### 6. Gemini Makes a Decision

Gemini returns one of three decisions:

#### `respond`

The issue is clearly covered by a knowledge article.

The solution is added to the incident, and the incident is resolved.

#### `ask`

The issue may match a knowledge article, but some important information is missing.

Gemini creates a question asking for the missing information.

#### `escalate`

There is no suitable knowledge article for the issue.

The incident is escalated to human IT support.

### 7. ServiceNow Is Updated

FastAPI sends the result back to ServiceNow and updates the incident based on the Gemini decision.

The overall flow is:

```text
ServiceNow
    ↓
Business Rule
    ↓
POST /webhook
    ↓
FastAPI
    ↓
Google Gemini
    ↓
kb_articles.json
    ↓
Decision
    ↓
ServiceNow Update
```

## Troubleshooting

Here are some common setup problems you may face:

### Server does not start

Make sure:

* The virtual environment is activated.
* All required packages are installed.
* The `.env` file contains the required values.

### ServiceNow connection problem

Check that:

* `SN_INSTANCE_URL` is correct.
* The URL starts with `https://`.
* Your ServiceNow credentials are correct.

### Webhook does not receive data

If you are testing locally:

* Make sure the FastAPI application is running.
* Make sure the tunneling tool is running.
* Make sure the webhook URL in ServiceNow is correct.

### Knowledge Base Not Found

Make sure that:

```text
kb_articles.json
```

is in the same project folder as:

```text
main.py
```

## Conclusion

This project provides an automated way to handle ServiceNow incidents using Google Gemini and a local knowledge base.

The main idea is:

```text
ServiceNow Incident
        ↓
FastAPI Webhook
        ↓
Gemini
        ↓
Knowledge Base
        ↓
Decision
        ↓
ServiceNow Update
```


