"""
Two ways to bring jobs into the pipeline:
  1. search_adzuna(...)   - pulls real, live listings from the free Adzuna API
  2. parse_manual_jobs()  - lets you paste in job descriptions/URLs yourself
Both return a list of dicts with the same shape so the rest of the app
doesn't need to care where a job came from.

Job IDs are deterministic (hashed from the job's URL, or its title+company+
description when there's no URL) rather than random, so re-searching or
re-generating for the same real-world job produces the SAME id instead of a
duplicate entry — that's what keeps your job queue and tracker from filling
up with repeats of the same posting.
"""
import hashlib
import re
import requests

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def _stable_id(title, company, url):
    key = url.strip() if url else f"{title}|{company}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def _job_dict(title, company, location, description, url, salary=None, source="adzuna"):
    return {
        "id": _stable_id(title, company, url),
        "title": title or "(untitled)",
        "company": company or "(unknown company)",
        "location": location or "",
        "description": description or "",
        "url": url or "",
        "salary": salary or "",
        "source": source,
    }


def search_adzuna(app_id, app_key, country, what, where="", results_wanted=50,
                   salary_min=None, full_time=True, remote_only=False):
    """
    Pulls live job listings from Adzuna (https://developer.adzuna.com/ - free tier
    gives 250 calls/month, no credit card required). Adzuna paginates 20 results
    per page, so this pages through until it has results_wanted or runs out.
    """
    if not app_id or not app_key:
        raise ValueError("Adzuna app_id/app_key are missing. Get a free key at "
                          "https://developer.adzuna.com/ and add it in the sidebar or .env")

    jobs = []
    page = 1
    per_page = 20
    while len(jobs) < results_wanted:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": per_page,
            "what": what,
            "content-type": "application/json",
        }
        if where:
            params["where"] = where
        if salary_min:
            params["salary_min"] = salary_min
        if full_time:
            params["full_time"] = 1
        if remote_only:
            # Adzuna doesn't have a strict remote filter; nudge the query instead
            params["what_or"] = "remote"

        resp = requests.get(ADZUNA_BASE_URL.format(country=country, page=page),
                             params=params, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Adzuna API error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for r in results:
            jobs.append(_job_dict(
                title=r.get("title", "").strip(),
                company=(r.get("company") or {}).get("display_name", ""),
                location=(r.get("location") or {}).get("display_name", ""),
                description=r.get("description", ""),
                url=r.get("redirect_url", ""),
                salary=_format_salary(r),
            ))
            if len(jobs) >= results_wanted:
                break

        page += 1
        if page > 25:  # safety cap
            break

    return jobs[:results_wanted]


def _format_salary(r):
    lo, hi = r.get("salary_min"), r.get("salary_max")
    if lo and hi:
        return f"{lo:,.0f} - {hi:,.0f}"
    if lo:
        return f"from {lo:,.0f}"
    return ""


def parse_manual_jobs(raw_text):
    """
    Parses jobs pasted in manually. Supports two formats:

    1. Simple: separate multiple job postings with a line of dashes ('---'),
       and inside each block, put the first line as "Title @ Company",
       optionally a line starting with 'URL:', then the description.

    2. Fallback: if no '---' separators are found, treats the whole
       paste as one single job description.
    """
    blocks = [b.strip() for b in re.split(r"^\s*-{3,}\s*$", raw_text, flags=re.MULTILINE) if b.strip()]
    if not blocks:
        return []

    jobs = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue

        title, company = lines[0], ""
        if "@" in lines[0]:
            title, company = [p.strip() for p in lines[0].split("@", 1)]

        url = ""
        body_lines = lines[1:]
        remaining = []
        for l in body_lines:
            if l.strip().lower().startswith("url:"):
                url = l.split(":", 1)[1].strip()
            else:
                remaining.append(l)

        description = "\n".join(remaining).strip()
        jobs.append(_job_dict(title=title, company=company, location="",
                               description=description, url=url, source="manual"))
    return jobs
