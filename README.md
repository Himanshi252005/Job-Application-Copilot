# Job Application Copilot

A local job-search agent with a web-based UI (Streamlit). Runs entirely on your
own machine. It:

- Pulls live job listings from the free **Adzuna** API, and/or lets you paste
  job descriptions in manually
- Generates a **tailored, ATS-friendly resume (.docx) + cover letter (.docx)**
  for each job, using your real resume content only — it never invents
  experience, employers, or skills you don't have
- Gives each job an honest **ATS match score** and lists matched vs. missing
  keywords, so you know your real odds, not an inflated number
- Can process **50–100 jobs in one batch**, in parallel
- Tracks everything in a local SQLite database so your history persists

## What it deliberately does *not* do

It does **not** log into job sites and auto-submit applications for you.
Almost every job board and ATS (LinkedIn, Indeed, Workday, Greenhouse, etc.)
prohibits automated submissions in their Terms of Service, and many actively
detect and reject bot-submitted applications — which would hurt your chances,
not help them. Instead, for every job you get a ready-to-go tailored resume
+ cover letter and a one-click link to the real job posting, so the final
"attach and submit" step — which differs on every site — takes you seconds.

## Setup

```bash
cd job_agent
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Choose a free AI provider for tailoring (pick one)

| Provider | Cost | Setup | Notes |
|---|---|---|---|
| **Groq** (default) | Free, no card | Get a key at https://console.groq.com/keys | Fast cloud inference. Use `openai/gpt-oss-120b` (best quality) or `openai/gpt-oss-20b` (fastest) — `llama-3.3-70b-versatile` is Enterprise-only now and will 404 on free accounts. ~1K req/min and a generous daily token cap on the free tier. |
| **Ollama** | Free, no signup at all | Install https://ollama.com, then `ollama pull llama3.1:8b` | Runs fully on your machine, works offline, no rate limits — but needs a reasonably capable computer and is slower per job. |
| **Google Gemini** | Free tier, no card | Get a key at https://aistudio.google.com/apikey | ~500 req/day on Flash models. |
| **Anthropic Claude** | Paid | Get a key at https://console.anthropic.com/settings/keys | Optional — highest quality writing if you want to pay for it later. |

Set your choice in the sidebar dropdown when the app is running, or set
`PROVIDER=` in `.env`. Groq is the default and is a good balance of quality,
speed, and being genuinely free.

### Job search key

**Adzuna API key** (for live job search — optional if you'll paste jobs
manually instead): free, instant signup at https://developer.adzuna.com/,
no credit card, 250 calls/month on the free tier, plenty for this.

Put your keys in a `.env` file (copy `.env.example` → `.env` and fill it in)
or just paste them into the sidebar when the app is running — sidebar keys
are kept only in memory for that session, never written to disk.

## Run it

```bash
streamlit run app.py
```

This opens the UI in your browser at `http://localhost:8501`, running
entirely locally.

## Using it

1. **Tab 1 — Resume**: enter your name/contact line, upload your resume
   (.pdf/.docx/.txt), and check the extracted text looks right.
2. **Tab 2 — Find Jobs**: set title/region/salary/remote preferences and
   click search to pull live listings, and/or paste job descriptions
   manually (separate multiple postings with a line of `---`).
3. **Tab 3 — Generate**: click generate. It tailors + builds documents for
   every queued job in parallel (adjust the parallelism slider if you hit
   rate limits), then shows each job with its ATS score, downloadable
   tailored resume/cover letter, and an "Open job & apply" link.
4. **Tab 4 — Tracker**: see your full history and applied status.

## Notes on cost and rate limits

Running 100 jobs through the AI tailoring step is 100 API calls. All four
providers are free or effectively free at this scale (see the table above),
but each free tier has a rate limit — keep parallelism modest (2–4, lower
for Ollama) to avoid 429 errors. The app reports any job that fails so you
can retry just those rather than the whole batch.

## Customizing

- `resume_builder.py` controls the resume's visual layout — edit freely,
  just keep it single-column with no tables/text boxes/images if you want
  to stay ATS-safe.
- `ai_tailor.py`'s `SYSTEM_PROMPT` controls how aggressively content gets
  rewritten — it's currently set to never fabricate experience; you can
  adjust tone/style there.
- `job_search.py` can be extended with other job-board APIs the same way
  `search_adzuna()` is written, if you want more sources than Adzuna.
