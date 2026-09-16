# 📧 Email Agent — Autonomous Gmail Triage with LangGraph

![Python](https://img.shields.io/badge/Python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-green)
![Gemini](https://img.shields.io/badge/LLM-Gemini%2FGemma-orange)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📸 Demo

![Labeled Gmail Inbox](screenshots/labeled-inbox.png)

An autonomous AI agent that reads your Gmail inbox, classifies emails across 20+ real-world categories, applies labels automatically, and drafts replies for human review — running on a **fully automated, zero-cost schedule** via GitHub Actions.

Built as a personal solution to a real problem: commercial AI email tools (Gemini for Workspace, Copilot, etc.) cap free-tier usage too aggressively for daily inbox management. This agent runs entirely on free-tier infrastructure, indefinitely.

---

## 🎯 Why This Exists

Job hunting and daily inbox triage generate a constant stream of job alerts, course updates, recruiter messages, and the occasional genuinely urgent email that needs a fast reply. Manually sorting this every day is repetitive and easy to fall behind on.

This agent automates the sorting, surfaces what's actually important, and drafts replies for anything that needs a response — while keeping a human firmly in the loop before anything is ever sent.

---

## ✨ Features

- **Multi-label classification** — 21 categories covering jobs, education, finance, urgency, and more (see full list below)
- **Real Gmail labels** — classifications are written back as actual, visible Gmail labels, auto-created on first use
- **Human-in-the-loop drafting** — the agent writes reply drafts for emails needing a response, saved directly to Gmail's Drafts folder. **It never auto-sends.** You review, edit, and send manually
- 🤖 **Genuine agentic decision-making** — an LLM bound with real tools (`draft_reply`, `flag_for_review`, `archive_no_action`) chooses the action per email, not a hardcoded rule
- ✍️ Drafts replies for human approval — never auto-sends
- **Idempotent by design** — a Supabase-backed tracking layer ensures no email is ever reclassified or re-drafted across runs, even if a run partially fails
- **Multi-model rate-limit resilience** — automatically falls back across multiple free-tier Gemini/Gemma models if one hits its quota, since each model has an independent rate limit
- **Fully autonomous scheduling** — runs 6x/day via GitHub Actions, at zero cost, with no server to maintain

---

## 🏷️ Classification Labels

The agent classifies each email into one or more of the following:

**Career:** `Job-Alert`, `Application-Update`, `Shortlisted`, `Interview-Invite`, `Rejection`, `Offer`, `Recruiter-Outreach`
**Education:** `Course-Update`, `Education-Opportunity`, `Webinar-Event`
**Finance:** `Subscription-Expiring`, `Billing-Invoice`, `Finance-Alert`
**Urgency:** `Urgent-Reply-Needed`, `Needs-Reply`, `Deadline-Reminder`
**General:** `Personal`, `Newsletter`, `Promotional`, `Spam`, `Other`

Emails can carry multiple labels — e.g., a shortlisting email might be tagged both `Shortlisted` and `Urgent-Reply-Needed`.

---
## 🏗️ Architecture

![Architecture diagram](screenshots/email_agent_architecture.png)

The agent runs as a scheduled LangGraph pipeline with a genuine agentic decision core: after classification and labeling, an LLM is given real tools (`draft_reply`, `flag_for_review`, `archive_no_action`) and **decides for itself** which action fits ordinary email. A deterministic priority guard protects urgent categories and high-scoring messages before the LLM can dismiss them.

1. **Fetch Unread** — Pulls unread emails from Gmail via the Gmail API
2. **Filter Seen** — Checks Supabase to skip emails already processed in a prior run
3. **Classify** — Each email is classified in parallel (`Send()` fan-out) across 21 labels, an importance score, and a `needs_reply` flag, using a Gemini/Gemma fallback chain. Email content is treated as untrusted data in prompts.
4. **Apply Labels** — Classification results are written back as real Gmail labels
5. **Priority Protection** — `Urgent-Reply-Needed`, `Interview-Invite`, `Shortlisted`, `Offer`, `Finance-Alert`, and scores of 0.8 or higher are marked `Needs-Reply`, starred, and marked important without relying on an LLM decision.
6. **Agent Decision** — Other emails are handed to an LLM bound with three tools. The model reasons about the email and calls exactly one:
   - `draft_reply` — writes a reply and saves it to Gmail Drafts
   - `flag_for_review` — labels it `Needs-Reply` for manual attention, without drafting anything
    - `archive_no_action` — removes the Gmail `INBOX` label for ordinary mail that needs no action
7. **Mark Processed** — Only successfully handled email IDs are recorded in Supabase. Failed classifications or actions remain eligible for retry.

**Human-in-the-loop stays intact regardless of the agent's choice** — `draft_reply` only ever creates a Gmail draft. Nothing is ever sent automatically.

**Key LangGraph & agentic patterns used:**

| Pattern | Where | Why |
|---|---|---|
| `Send()` fan-out | Classification, per-email agent loop | Parallel processing instead of sequential |
| Tool-calling (`bind_tools`) | Agent decision node | The LLM genuinely chooses the action — not a fixed if/else |
| Multi-model fallback | Both classification and tool-calling | Resilience against free-tier rate limits, confirmed working across all 4 models |
| State reducers | `Annotated[list, add]` | Merges parallel `Send()` outputs safely |
| Human-in-the-loop | Draft-only, never auto-send | A human decision point before anything leaves the inbox, regardless of agent choice |


## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Google Gemini / Gemma (multi-model fallback chain) |
| Email | Gmail API (OAuth2, refresh-token flow) |
| Persistence | Supabase (Postgres) |
| Deployment | GitHub Actions (scheduled cron, zero cost) |
| Language | Python 3.11 |

---

## 📂 Project Structure

```text
Email Agent/
├── main.py                    # Entry point
├── requirements.txt
├── src/
│   ├── auth/
│   │   └── gmail_auth.py      # OAuth refresh-token flow
│   ├── gmail/
│   │   ├── fetch.py           # Fetch + parse unread emails
│   │   ├── labels.py          # Apply Gmail labels
│   │   └── drafts.py          # Create threaded Gmail drafts
│   ├── llm/
│   │   ├── client.py          # Multi-model fallback LLM client
│   │   └── prompts.py         # Classification + draft prompts
│   ├── graph/
│   │   ├── state.py           # LangGraph state schema
│   │   ├── nodes.py           # All graph nodes
│   │   ├── edges.py           # Send() routing logic
│   │   └── build_graph.py     # Compiled graph
│   └── storage/
│       └── processed_store.py # Supabase idempotency layer
└── .github/workflows/
    └── email_agent.yml        # Scheduled GitHub Actions workflow
```

---

## 🚀 Setup (If You Want to Run This Yourself)

### 1. Prerequisites
- Python 3.11+
- A Google Cloud project with Gmail API enabled
- A Google AI Studio API key (Gemini/Gemma)
- A free Supabase account

### 2. Clone the Repo
```bash
git clone https://github.com/Jawad-Emre/Agentic-Ai-Projects.git
cd "Agentic-Ai-Projects/Email Agent"
```

### 3. Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
python -m pip install -r requirements.txt
```

### 4. Set Up Google OAuth
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Configure the OAuth consent screen (add yourself as a test user, or publish the app)
4. Create OAuth credentials (Desktop app type), download `credentials.json` into this folder

### 5. Generate a Refresh Token
```bash
python token_generation.py
```
This opens a browser for one-time authorization and prints your refresh token.

> **Note:** Unverified Google apps issue refresh tokens that expire every 7 days. This is a known limitation for personal-use OAuth apps without full Google verification.

### 6. Set Up Supabase
1. Create a project at [supabase.com](https://supabase.com)
2. Create a table named `processed_emails` with columns: `id` (text, primary key), `processed_at` (timestamptz, default `now()`)
3. Copy your Project URL and Secret API key

### 7. Configure Environment Variables
Create a `.env` file:
```env
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_secret_key
```

### 8. Run Locally
```bash
python main.py
```

### 9. Deploy (Optional — Automated Scheduling)
1. Push this repo to your own GitHub
2. Add all 6 environment variables above as **GitHub repo secrets** (Settings → Secrets and variables → Actions)
3. The included `.github/workflows/email_agent.yml` will run automatically on schedule — no server needed

---

## ⚠️ Known Limitations

- **7-day token expiry** — unverified Google OAuth apps require re-authorization weekly. A quick manual `token_generation.py` re-run + secret update is needed periodically.
- **Free-tier rate limits** — heavy inbox volume can occasionally exhaust all fallback models in a single run; those emails are left unprocessed so a later scheduled run can retry them.
- **Batch size** — each run fetches up to 10 unread messages, using Gmail pagination when more are available. Remaining messages are handled by later runs.
- **Priority protection** — important categories and high-scoring messages are starred, marked important, and flagged for review instead of being archived automatically.
- **No auto-send** — by design. This agent will never send an email without you manually clicking send in Gmail.

---

## 📄 License

MIT — free to use, modify, and learn from.

---

## 🙋 About This Project

Built as a hands-on project to learn LangGraph's core patterns: parallel execution via `Send()`, conditional routing, state reducers, and human-in-the-loop design — applied to a real, personally useful problem rather than a toy example.