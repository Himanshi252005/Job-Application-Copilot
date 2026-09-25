"""
Calls an AI provider to, for a single job:
  - rewrite the resume's summary + bullet points to match the job description
  - pick out the important ATS keywords and confirm which ones are covered
  - write a short tailored cover letter
Returns structured JSON so resume_builder.py can lay it out cleanly.

Supports four providers, chosen via `provider`:
  - "groq"      free, no credit card, fast cloud inference (recommended default)
  - "ollama"    free, fully local/offline, needs Ollama installed + a model pulled
  - "gemini"    free tier, no credit card, Google's cloud API
  - "anthropic" paid, highest quality writing
All four are prompted identically so output quality/shape stays consistent.
"""
import json
import re
import time
import requests

SYSTEM_PROMPT = """You are an expert resume writer and ATS (Applicant Tracking System) optimization \
specialist. You NEVER invent experience, employers, titles, dates, or skills the candidate doesn't \
have. You only rephrase, reorder, emphasize, and select from what is already true in the candidate's \
original resume, using language and keywords that match the target job description. If the resume \
genuinely lacks a skill the job wants, you leave it out rather than fabricate it.

Respond with ONLY a single valid JSON object, no markdown fences, no commentary, matching exactly \
this schema:
{
  "tailored_headline": "string, a one-line professional title/headline",
  "tailored_summary": "string, 2-3 sentences",
  "key_skills": ["string", "..."],            // 8-12 skills, prioritized for this job, drawn only from the original resume
  "experience_bullets": [                        // rewritten bullets grouped by the original resume's roles, in original order
    {
      "role": "string - copy exactly from original resume",
      "company": "string - copy exactly from original resume",
      "dates": "string - copy exactly from original resume",
      "bullets": ["string", "..."]              // 2-3 bullets per role, keep each under 20 words
    }
  ],
  "education": ["string - copy from original resume, lightly reformatted only"],
  "matched_keywords": ["string", "..."],       // job-description keywords genuinely present in the candidate's background
  "missing_keywords": ["string", "..."],       // important job-description keywords the candidate's resume does NOT support - be honest
  "ats_match_score": 0,                          // integer 0-100, realistic estimate of keyword/skill overlap, do not inflate
  "cover_letter": "string, 3 SHORT paragraphs (under 220 words total), no placeholders like [Company Name] left unfilled"
}

Be concise everywhere. Respond with ONLY the JSON object. No markdown fences, no preamble, no explanation."""

USER_TEMPLATE = """CANDIDATE'S ORIGINAL RESUME:
---
{resume_text}
---

TARGET JOB:
Title: {job_title}
Company: {company}
Description:
---
{job_description}
---

Tailor the resume content and write the cover letter for this specific job, following the system \
instructions exactly. Return only the JSON object."""

# Free-tier token budgets are small (Groq's default free tier is ~8000 tokens
# PER MINUTE total, shared across input+output). Keep prompts and output
# tight so a single call comfortably fits, and retries don't compound the
# problem.
MAX_RESUME_CHARS = 5000
MAX_JOB_DESC_CHARS = 2500
MAX_OUTPUT_TOKENS = 1600

RETRY_WAIT_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)


def _retry(fn, max_attempts=5):
    """Calls fn() and, on a 429 rate-limit error, sleeps for the time the API
    tells us to wait (parsed from its own error message) and retries, up to
    max_attempts times. Falls back to exponential backoff if no wait hint is
    present."""
    last_err = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except RateLimitError as e:
            last_err = e
            match = RETRY_WAIT_RE.search(str(e))
            wait_s = float(match.group(1)) + 0.5 if match else min(2 ** attempt, 20)
            time.sleep(wait_s)
    raise last_err


class RateLimitError(RuntimeError):
    pass


def tailor_for_job(provider: str, creds: dict, resume_text: str, job: dict) -> dict:
    user_prompt = USER_TEMPLATE.format(
        resume_text=resume_text[:MAX_RESUME_CHARS],
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        job_description=job.get("description", "")[:MAX_JOB_DESC_CHARS],
    )

    if provider == "groq":
        raw = _retry(lambda: _call_groq(creds["api_key"], creds["model"], user_prompt))
    elif provider == "ollama":
        raw = _call_ollama(creds["base_url"], creds["model"], user_prompt)
    elif provider == "gemini":
        raw = _retry(lambda: _call_gemini(creds["api_key"], creds["model"], user_prompt))
    elif provider == "anthropic":
        raw = _retry(lambda: _call_anthropic(creds["api_key"], creds["model"], user_prompt))
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return _extract_json(raw)


def _call_groq(api_key: str, model: str, user_prompt: str) -> str:
    if not api_key:
        raise ValueError("Missing Groq API key. Get a free one at https://console.groq.com/keys")
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    if resp.status_code == 429:
        raise RateLimitError(resp.text[:400])
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:400]}")
    return resp.json()["choices"][0]["message"]["content"]


def _call_ollama(base_url: str, model: str, user_prompt: str) -> str:
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.4},
            },
            timeout=180,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not reach Ollama. Make sure it's installed and running "
            "(https://ollama.com), and that you've pulled the model with: "
            f"`ollama pull {model}`"
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:400]}")
    return resp.json()["message"]["content"]


def _call_gemini(api_key: str, model: str, user_prompt: str) -> str:
    if not api_key:
        raise ValueError("Missing Gemini API key. Get a free one at https://aistudio.google.com/apikey")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"Content-Type": "application/json"},
        params={"key": api_key},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json",
                                  "maxOutputTokens": MAX_OUTPUT_TOKENS},
        },
        timeout=60,
    )
    if resp.status_code == 429:
        raise RateLimitError(resp.text[:400])
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_anthropic(api_key: str, model: str, user_prompt: str) -> str:
    import anthropic
    if not api_key:
        raise ValueError("Missing Anthropic API key.")
    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=model, max_tokens=MAX_OUTPUT_TOKENS, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.RateLimitError as e:
        raise RateLimitError(str(e))
    return "".join(block.text for block in message.content if block.type == "text")


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse AI response as JSON: {e}\nRaw: {raw[:500]}")
