# AI Email Automation System

An autonomous email management agent that reads, classifies, and replies to incoming emails using the **Gmail API** and **Google Gemini AI** — with full conversation context tracking and an inline HTML signature.

## How It Works

1. Polls Gmail every 30 seconds for unread emails from the last 30 minutes
2. Strips quoted reply threads using `email-reply-parser` to isolate only the new message
3. Retrieves conversation history from SQLite for context-aware responses
4. Sends the email to Gemini with a custom system prompt (persona + length limits)
5. Replies with an HTML-formatted email and an inline PNG signature
6. Marks the email as read and saves the exchange to history

## Features

- **Smart Filtering** — skips newsletters, no-reply addresses, and known platforms (LinkedIn, GitHub, Binance, etc.)
- **Thread-Aware** — maintains per-thread conversation history (last 10 messages) via SQLite
- **Inline Signature** — attaches a transparent PNG as a CID image for an authentic-looking reply
- **Rate Limit Safe** — responses capped at 120–150 words to stay within Google's free tier quota
- **Multi-language** — automatically detects sender's language and replies accordingly

## Setup

### 1. Clone & install

```bash
git clone https://github.com/mmeekh/Email-Automation-with-AI.git
cd Email-Automation-with-AI
pip install -r requirements.txt
```

### 2. Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable the **Gmail API**
3. Create **OAuth 2.0 credentials** (Desktop app type) → download as `credentials.json`
4. Place `credentials.json` in the project root

### 3. Environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TARGET_DOMAIN=yourdomain.com   # optional: restrict replies to a specific domain
```

### 4. Signature (optional)

Place a `signature.png` file in the root directory. It will be embedded as an inline image in every reply.

### 5. Run

```bash
python main.py
```

On first run, a browser window will open for Gmail OAuth. After that, `token.json` is cached for future runs.

## Tech Stack

| Component | Tech |
|---|---|
| AI Model | Google Gemini 2.5 Flash Lite |
| Email API | Gmail API (`google-api-python-client`) |
| Thread Parsing | `email-reply-parser` |
| Storage | SQLite |
| Auth | OAuth 2.0 with auto token refresh |

## Configuration

Edit the `system_instruction` string in `main.py` to change the AI's persona, response language rules, or word count limits.

---

Built by [Muhammet Emin Kilic](https://linkedin.com/in/emin-kilic-250b14210)
