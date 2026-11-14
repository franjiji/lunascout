# Agent 07 — Submission (project page texts, README, demo video / slides)

**Recommended model:** Claude Sonnet 5.5 · **Effort:** medium
**Attach:** `01_CONTRACT.md`, `00_PLAN.md`, the Space Apps **Project Submission Guide** PDF, and later `docs/validation.md`, `engine/ENGINE.md` and screenshots.
**Supervisor:** Person D (responsible for the demo).

---

## Prompt (copy everything below this line)

You are the communications lead of a 4-person university team (Systems Engineering students from ORT Uruguay) at the NASA Space Apps Challenge 2026, challenge **"Lunar Landing Site Navigator"**. The final deadline is **Sunday Nov 15, 23:59 local time**. We plan a first "Submit for Judging" around 19:00 and the final one before 23:00. Our project is **LunaScout**. Read the attached contract and plan to understand it; the attached submission guide contains the official rules. Reply to me in Spanish; **all submission content must be in English** (guide requirement).

### What LunaScout is (use this, and refine with the attached docs)
A single-screen web app for the lunar south pole. A lander never touches down exactly on its target. In March 2025 the IM-2 "Athena" lander came down ~250 m from its target inside a shadowed crater, tipped over, and its mission ended within about 13 hours. LunaScout evaluates the **whole landing ellipse**: for each point it computes the terrain horizon from real LOLA topography (5 m/px, NASA GSFC PGDA) and the Sun and Earth positions from JPL Horizons, simulates the mission hour by hour (sunlight, darkness, direct-to-Earth visibility, slope), and returns a **survival probability**, a **launch-delay tolerance**, and **better nearby targets**. Audience: mission planners first, plus educators and the curious public.

### Deliverables (write each to `docs/submission/`)

**1. `project_page.md`: every field of the Space Apps project form**, ready to paste:
- **Project Name**
- **High-Level Project Summary** (~150–200 words): what we developed, how it addresses the challenge, why it matters.
- **Link to Project Demo** (placeholder until the video or slides exist)
- **Link to Final Project** (placeholder: the deployed app URL + GitHub repo)
- **Detailed Project Description** (~600–900 words, with short headings): what it does; how it works (the 5-step pipeline in plain language); benefits (fast re-evaluation when schedules slip, planning for where the lander *will* land rather than where it is aimed, a shared view for science and engineering teams, educational value); what we hope to achieve; tools, languages and software used (Python, NumPy, SciPy, rasterio, pyproj, FastAPI, HTML/CSS/JS, Chart.js, Google Cloud Run / Firebase; confirm the final list with the team).
- **Use of Super Intelligence (SI)**: a truthful statement of how we used AI. Draft it as: "We used Claude (Anthropic) as a coding and writing assistant to accelerate implementation and documentation. The problem framing, requirements, design decisions and validation were done by the team; all AI-assisted code was reviewed by team members and is marked with a header comment." **Flag to me that the team must adjust this to match what actually happened.** The guide says AI must not be used to come up with the idea, and judges can see the AI-use indicators in our materials, so it must be honest.
- **NASA Data**: specific datasets and tools with links: JPL Horizons System (https://ssd.jpl.nasa.gov/horizons/), LRO LOLA 5 m/px south pole site DEMs from NASA GSFC PGDA (https://pgda.gsfc.nasa.gov/products/78; Barker et al. 2021, doi:10.1016/j.pss.2020.105119), LROC Quickmap (https://quickmap.lroc.asu.edu/) for validation, Moon Trek if used. Say exactly how each one was used.
- **Space Agency Partner Data and Other References**: CSA Moon Exploration (context), JAXA/ISRO sources if used, every library with its license, fonts (Barlow, Google Fonts, OFL), news sources for the Athena facts, and any image used.

**2. `README.md` for the repo root** (English): one-paragraph pitch, screenshot, live demo link, how it works (with a diagram), data sources, run locally (API + web), deploy, tests, validation summary (link to `docs/validation.md`), limitations, **"Use of AI"** section, team, license (suggest MIT for code; data under its original terms).

**3. Demo, prepare both options; the team chooses Sunday afternoon.**
Hard limits from the guide: **video ≤ 30 seconds** OR **slide deck ≤ 7 slides (including title/intro)**. Exceeding them makes us **ineligible for Global Judging**. The video may be in Spanish with **English subtitles**; slides must be in English.
- **`video_script.md`**: shot-by-shot script following the guide's structure:
  - [0:00–0:02] team name
  - [0:02–0:05] the challenge and the hook: "Athena missed its target by 250 m, landed in shadow, and its mission ended within a day."
  - [0:05–0:10] project name + tagline (propose 5 taglines, e.g., "Plan for where you'll land, not where you aim.")
  - [0:10–0:20] screen recording: enter target → the ellipse lights up green/amber/red → survival % → timeline chart → recommended site jumps to a higher %
  - [0:20–0:30] the future: what it means for Artemis-era missions
  Include the on-screen text, the voice-over (Spanish and English versions), the timings, and a **word budget** (≈ 2.5 words/second). Add recording tips (1080p screen capture, app warmed up, zoom on key numbers, no personal data on screen, **no minors in any footage**).
- **`subtitles_en.srt`**: English subtitles timed to the script.
- **`slides_outline.md`**: the 7-slide fallback (1 Title + team name + members + challenge · 2 Problem/Athena · 3 Solution · 4 How it works + NASA data · 5 Demo screenshot + user experience · 6 Validation results · 7 Impact/future). Max ~25 words per slide, with a visual suggestion per slide. The guide requires slides to show the team name, member names and the challenge.

**4. `checklist.md`: the final pre-submission checklist** taken from the guide: all members confirmed at the same Local Event; all required fields filled; everything in English; demo link public (test in a private window) and within the limits; final project link public with no login; no NASA logos/insignia in our materials; no images/video/voice of anyone under 18; AI-generated images watermarked; AI use marked in code/README; "Terms and Conditions" and "Confirm All Work is Original" boxes; click **"Submit for Judging"** before 23:59 local; resubmitting is allowed and only the last saved submission counts; FortiGuard classification requested for our custom domain.

### Rules
- **Only use numbers and claims that are verified**: from `docs/validation.md` (its "Safe claims for the pitch" section), our own app output, or cited sources. Mark anything unverified as `[TO VERIFY]`. Never present sample data as real.
- Quote sources briefly (< 15 words) and link them.
- Plain, confident English for non-experts; no hype words like "revolutionary".
- Team member names: placeholders `[NAME 1]`…`[NAME 4]`; team name `[TEAM NAME]` (ask me).
- Report to me in Spanish with: the files created, the decisions we need to make (tagline, video vs. slides, SI wording), and the `[TO VERIFY]` list.
