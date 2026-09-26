import os
import time
import uuid
import concurrent.futures as cf

import streamlit as st

import config
import resume_parser
import job_search
import ai_tailor
import resume_builder
import tracker

OUTPUT_DIR = "generated_applications"
os.makedirs(OUTPUT_DIR, exist_ok=True)
tracker.init_db()

st.set_page_config(page_title="Job Application Copilot", layout="wide", page_icon="🧭")

# Give every visitor their own private session ID so the shared tracker.db
# file on the server never mixes one person's resume/job history with
# another's — see the big comment at the top of tracker.py.
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ---------------------------------------------------------------- theme / CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap');

:root {
    --bg: #12141A;
    --card: #1A1D24;
    --card-hover: #20242D;
    --border: #2A2E38;
    --accent1: #8B5CF6;
    --accent2: #EC4899;
    --text: #E9E9EE;
    --muted: #9599A6;
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; color: var(--text); }

.stApp { background: var(--bg); }
section[data-testid="stSidebar"] { background: #0F1116; border-right: 1px solid var(--border); }

.main .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px; }

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, rgba(139,92,246,0.18) 0%, rgba(236,72,153,0.18) 100%);
    border: 1px solid var(--border);
    padding: 2.2rem 2.6rem;
    border-radius: 22px;
    margin-bottom: 1.8rem;
    box-shadow: 0 10px 30px rgba(139,92,246,0.12);
}
.hero-banner h1 {
    font-family: 'Poppins', sans-serif;
    background: linear-gradient(135deg, var(--accent1) 0%, var(--accent2) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin: 0 0 .4rem 0; font-size: 2.1rem; letter-spacing: -0.5px;
}
.hero-banner p { color: var(--muted); margin: 0; font-size: 1rem; line-height: 1.55; max-width: 760px; }

/* Section labels */
.section-label {
    font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 1.05rem;
    color: #C4B5FD; margin: .2rem 0 .8rem 0; letter-spacing: .2px;
}

/* Buttons */
.stButton>button, .stDownloadButton>button {
    border-radius: 999px !important; font-weight: 600 !important;
    border: none !important; color: white !important;
    background: linear-gradient(135deg, var(--accent1) 0%, var(--accent2) 100%) !important;
    transition: all .18s ease;
}
.stButton>button:hover, .stDownloadButton>button:hover {
    transform: translateY(-2px); box-shadow: 0 8px 22px rgba(139,92,246,0.35);
}
.stLinkButton a {
    border-radius: 999px !important; font-weight: 600 !important; color: white !important;
    background: linear-gradient(135deg, var(--accent1) 0%, var(--accent2) 100%) !important;
    border: none !important;
}
.stLinkButton a:hover { box-shadow: 0 8px 22px rgba(139,92,246,0.35); }

/* Tabs → pill nav */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: none !important; }
.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important; padding: 8px 20px !important;
    background: var(--card); font-weight: 600; color: var(--muted);
    border: 1px solid var(--border);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent1) 0%, var(--accent2) 100%) !important;
    color: white !important; border: none !important;
}

/* Expander → job cards */
[data-testid="stExpander"] {
    border-radius: 16px !important;
    border: 1px solid var(--border) !important;
    background: var(--card);
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    margin-bottom: .7rem;
    overflow: hidden;
}

/* Dataframe / tracker */
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--border); }

/* Score pills */
.score-pill {
    display: inline-block; padding: 3px 12px; border-radius: 999px;
    font-weight: 700; font-size: .82rem; margin-right: 6px;
}
.score-high { background: rgba(52,211,153,0.15); color: #34D399; }
.score-mid  { background: rgba(251,191,36,0.15); color: #FBBF24; }
.score-low  { background: rgba(248,113,113,0.15); color: #F87171; }

/* Text inputs / selects */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
    border-radius: 10px !important; border-color: var(--border) !important;
    background: var(--card) !important;
}

/* Metric widgets (tracker tab) */
[data-testid="stMetric"] {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: .8rem 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-banner">
  <h1>🧭 Job Application Copilot</h1>
  <p>Runs locally on your machine. Finds jobs, tailors your resume + cover letter for each one,
  scores ATS match honestly, and gives you a one-click apply link per job. It does not auto-submit
  applications on job sites — most sites' Terms of Service prohibit that, and bot submissions often
  get auto-rejected anyway.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- session state
for key, default in [
    ("resume_text", ""), ("candidate_name", ""), ("contact_line", ""),
    ("jobs", []), ("results", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------- settings (all from .env, no UI)
# No sidebar, no provider/key widgets — everything for a live public demo
# comes silently from your .env file. If you ever want to switch provider
# or model, change PROVIDER / *_MODEL in .env and restart the app.
provider = config.PROVIDER if config.PROVIDER in ["groq", "ollama", "gemini", "anthropic"] else "groq"

creds = {}
if provider == "groq":
    creds = {"api_key": config.GROQ_API_KEY, "model": config.GROQ_MODEL}
elif provider == "ollama":
    creds = {"base_url": config.OLLAMA_BASE_URL, "model": config.OLLAMA_MODEL}
elif provider == "gemini":
    creds = {"api_key": config.GEMINI_API_KEY, "model": config.GEMINI_MODEL}
else:
    creds = {"api_key": config.ANTHROPIC_API_KEY, "model": config.CLAUDE_MODEL}

adzuna_id = config.ADZUNA_APP_ID
adzuna_key = config.ADZUNA_APP_KEY
country = config.ADZUNA_COUNTRY


def creds_ready():
    if provider == "ollama":
        return bool(creds.get("base_url")) and bool(creds.get("model"))
    return bool(creds.get("api_key"))


tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ Resume", "2️⃣ Find Jobs", "3️⃣ Generate", "4️⃣ Tracker"])

# ---------------------------------------------------------------- Tab 1: Resume
with tab1:
    st.markdown('<div class="section-label">📄 Upload your resume once</div>', unsafe_allow_html=True)
    st.session_state.candidate_name = st.text_input("Full name (for the generated documents)",
                                                      value=st.session_state.candidate_name)
    st.session_state.contact_line = st.text_input(
        "Contact line (email · phone · city · LinkedIn)", value=st.session_state.contact_line)

    uploaded = st.file_uploader("Resume (.pdf, .docx, or .txt)", type=["pdf", "docx", "txt"])
    if uploaded is not None:
        try:
            st.session_state.resume_text = resume_parser.parse_resume(uploaded.read(), uploaded.name)
            st.success(f"Parsed {len(st.session_state.resume_text)} characters from your resume.")
        except Exception as e:
            st.error(f"Couldn't parse that file: {e}")

    if st.session_state.resume_text:
        with st.expander("Preview extracted resume text"):
            st.session_state.resume_text = st.text_area(
                "You can fix any extraction errors here before tailoring:",
                value=st.session_state.resume_text, height=300)

# ---------------------------------------------------------------- Tab 2: Find Jobs
with tab2:
    st.markdown('<div class="section-label">🔍 Set your preferences and pull in jobs</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        job_title = st.text_input("Job title(s)", placeholder="e.g. Data Analyst")
    with col2:
        region = st.text_input("Region / city", placeholder="e.g. Bengaluru, or blank for anywhere")
    with col3:
        results_wanted = st.number_input("How many jobs to pull", min_value=5, max_value=100, value=50, step=5)

    col4, col5 = st.columns(2)
    with col4:
        salary_min = st.number_input("Minimum salary (optional, local currency)", min_value=0, value=0, step=10000)
    with col5:
        remote_only = st.checkbox("Prefer remote roles")

    if st.button("🔍 Search live jobs via Adzuna"):
        try:
            with st.spinner("Searching..."):
                found = job_search.search_adzuna(
                    adzuna_id, adzuna_key, country, what=job_title, where=region,
                    results_wanted=int(results_wanted),
                    salary_min=salary_min or None, remote_only=remote_only,
                )
            existing_ids = {j["id"] for j in st.session_state.jobs}
            st.session_state.jobs += [j for j in found if j["id"] not in existing_ids]
            st.success(f"Found {len(found)} jobs.")
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.markdown("**Or paste jobs in manually** — separate multiple postings with a line of `---`. "
                "First line of each block: `Title @ Company`. Optional `URL: https://...` line. Rest is the description.")
    manual_text = st.text_area("Paste job description(s) here", height=150)
    if st.button("➕ Add pasted jobs"):
        added = job_search.parse_manual_jobs(manual_text)
        st.session_state.jobs += added
        st.success(f"Added {len(added)} job(s).")

    st.divider()
    if st.session_state.jobs:
        st.write(f"**{len(st.session_state.jobs)} jobs in your queue:**")
        for j in st.session_state.jobs:
            st.write(f"- **{j['title']}** @ {j['company']} {('· ' + j['location']) if j.get('location') else ''}")
        if st.button("🗑️ Clear job queue"):
            st.session_state.jobs = []
            st.rerun()

# ---------------------------------------------------------------- Tab 3: Generate
with tab3:
    st.markdown('<div class="section-label">⚡ Generate tailored, ATS-friendly applications</div>', unsafe_allow_html=True)
    n_jobs = len(st.session_state.jobs)
    st.write(f"{n_jobs} job(s) queued.")

    if not st.session_state.resume_text:
        st.warning("Upload a resume in Tab 1 first.")
    elif not creds_ready():
        st.warning(f"No {provider.title()} key found in your `.env` file. Add it there and restart the app.")
    elif n_jobs == 0:
        st.warning("Add some jobs in Tab 2 first.")
    else:
        max_workers = st.slider(
            "Parallel requests (higher = faster, but watch your rate limits)",
            1, 8, 1 if provider in ("groq", "gemini") else 3,
            help="Groq and Gemini's free tiers are limited by TOKENS PER MINUTE, not just "
                 "request count — running jobs in parallel doesn't make you faster, it just "
                 "makes several requests compete for the same small budget and 429 sooner. "
                 "1 is recommended for free-tier cloud providers; the app auto-retries on "
                 "rate limits, so it'll just take a bit longer, not fail.",
        )
        if st.button(f"⚡ Generate tailored resume + cover letter for all {n_jobs} jobs"):
            progress = st.progress(0.0, text="Starting...")
            results = {}
            errors = []
            done = 0

            # Capture everything the worker threads need into plain local
            # variables first — st.session_state is tied to Streamlit's main
            # script thread and raises "no attribute" errors if touched from
            # a ThreadPoolExecutor worker thread.
            resume_text = st.session_state.resume_text
            candidate_name = st.session_state.candidate_name or "Your Name"
            contact_line = st.session_state.contact_line
            jobs_to_process = list(st.session_state.jobs)
            session_id = st.session_state.session_id

            def process(job):
                tailored = ai_tailor.tailor_for_job(provider, creds, resume_text, job)
                safe_name = "".join(c for c in f"{job['company']}_{job['title']}" if c.isalnum() or c in " _-")[:60]
                resume_path = os.path.join(OUTPUT_DIR, f"{safe_name}_resume.docx")
                cover_path = os.path.join(OUTPUT_DIR, f"{safe_name}_cover_letter.docx")
                resume_builder.build_resume_docx(candidate_name, contact_line, tailored, resume_path)
                resume_builder.build_cover_letter_docx(
                    candidate_name, contact_line, tailored.get("cover_letter", ""), cover_path)
                tracker.add_application(session_id, job, tailored.get("ats_match_score", 0), resume_path, cover_path)
                return job["id"], tailored, resume_path, cover_path

            with cf.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(process, job): job for job in jobs_to_process}
                for future in cf.as_completed(futures):
                    job = futures[future]
                    try:
                        job_id, tailored, resume_path, cover_path = future.result()
                        results[job_id] = {"job": job, "tailored": tailored,
                                            "resume_path": resume_path, "cover_path": cover_path}
                    except Exception as e:
                        errors.append(f"{job['title']} @ {job['company']}: {e}")
                    done += 1
                    progress.progress(done / n_jobs, text=f"{done}/{n_jobs} done")

            st.session_state.results = results
            if errors:
                st.error("Some jobs failed:\n" + "\n".join(errors))
            st.success(f"Generated {len(results)} tailored application(s). See below and in the Tracker tab.")

    if st.session_state.results:
        st.divider()
        st.markdown('<div class="section-label">✨ Tailored applications</div>', unsafe_allow_html=True)
        sorted_results = sorted(st.session_state.results.values(),
                                 key=lambda r: r["tailored"].get("ats_match_score", 0), reverse=True)
        grid_cols = st.columns(2)
        for idx, r in enumerate(sorted_results):
            job, tailored = r["job"], r["tailored"]
            score = tailored.get("ats_match_score", 0)
            tier_class = "score-high" if score >= 70 else "score-mid" if score >= 45 else "score-low"
            with grid_cols[idx % 2]:
                with st.expander(f"{job['title']} — {job['company']}", expanded=False):
                    st.markdown(
                        f'<span class="score-pill {tier_class}">{score}% ATS match</span>',
                        unsafe_allow_html=True,
                    )
                    st.write("")
                    st.write("**Matched keywords:**", ", ".join(tailored.get("matched_keywords", [])) or "—")
                    st.write("**Missing keywords:**", ", ".join(tailored.get("missing_keywords", [])) or "—")
                    st.write("**Tailored summary:**", tailored.get("tailored_summary", ""))
                    colA, colB, colC = st.columns(3)
                    with colA:
                        with open(r["resume_path"], "rb") as f:
                            st.download_button("⬇️ Resume", f, file_name=os.path.basename(r["resume_path"]),
                                                key=f"resume_{job['id']}")
                    with colB:
                        with open(r["cover_path"], "rb") as f:
                            st.download_button("⬇️ Cover letter", f, file_name=os.path.basename(r["cover_path"]),
                                                key=f"cover_{job['id']}")
                    with colC:
                        if job.get("url"):
                            st.link_button("🔗 Apply", job["url"], key=f"link_{job['id']}")
                    if st.button("✅ Mark as applied", key=f"applied_{job['id']}", use_container_width=True):
                        tracker.mark_applied(st.session_state.session_id, job["id"])
                        st.toast("Marked as applied!")

# ---------------------------------------------------------------- Tab 4: Tracker
with tab4:
    st.markdown('<div class="section-label">📋 Your application history</div>', unsafe_allow_html=True)
    rows = tracker.get_all(st.session_state.session_id)
    if not rows:
        st.info("No applications generated yet.")
    else:
        applied = sum(1 for r in rows if r["status"] == "applied")
        avg_score = round(sum(r["ats_score"] or 0 for r in rows) / len(rows)) if rows else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Generated", len(rows))
        c2.metric("Marked applied", applied)
        c3.metric("Avg. ATS match", f"{avg_score}%")
        st.write("")
        st.dataframe(
            [{"Title": r["title"], "Company": r["company"], "ATS %": r["ats_score"],
              "Status": r["status"], "Created": r["created_at"][:10],
              "Applied": (r["applied_at"] or "")[:10], "URL": r["url"]} for r in rows],
            use_container_width=True,
        )
