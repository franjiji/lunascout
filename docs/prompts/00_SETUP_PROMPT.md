# Prompt de arranque: armar el repo

**Dónde:** Claude Code, abierto en `C:\Users\ASUS\Desktop\lunar-landing--`
**Modelo:** Claude Sonnet 5.5 · **Esfuerzo:** low
**Cuándo:** primero de todo, antes de lanzar los agentes 02–05.

---

## Prompt (copy everything below this line)

Set up the project repository for our NASA Space Apps 2026 hackathon project "LunaScout". Reply to me in Spanish; everything in the repo must be in English.

Context: the folder ./prompts contains our plan (00_PLAN.md), the project context (CONTEXT.md), the shared contract (01_CONTRACT.md) and the prompts for 6 agents. Read CONTEXT.md, 00_PLAN.md and 01_CONTRACT.md first.

Do exactly this:
1. Create the folder ./lunascout with the structure from 00_PLAN.md ("Estructura del repo"): data/raw, data/ephemeris, data/derived, engine/ (with __init__.py and tests/), scripts/, api/, web/, fixtures/, docs/. Put a .gitkeep in empty folders.
2. Copy prompts/01_CONTRACT.md to lunascout/CONTRACT.md and prompts/CONTEXT.md to lunascout/CONTEXT.md.
3. Create lunascout/CLAUDE.md with these lines, so every future Claude Code session in the repo loads them:
   - "Read CONTEXT.md and CONTRACT.md before doing anything. CONTRACT.md is binding; don't change it without the team's approval."
   - "Reply to the user in Spanish. All code, comments, docs and UI text in English."
   - "Every code file starts with the AI-use header from CONTRACT.md section 7."
   - "Never present sample or made-up data as real. Sample data must be labeled."
   - "Work only in your own folder and branch (see 00_PLAN.md ownership). Ask before changing files owned by another agent."
4. Create fixtures/sample_response.json: a valid JSON example of the POST /api/analyze response in CONTRACT.md section 4.3, with "is_sample": true, ~40 points inside an ellipse, timeseries arrays of length n = 168, horizon_profile with 360 values, delay_curve for 0..30. Values must be plausible but are placeholders (the engine agent will replace them with real output). Validate that it parses and contains every field in the contract.
5. Move ./horizons_test.py to lunascout/scripts/horizons_test.py.
6. Copy the design reference folder "./LunaScout — Landing-site checker-html" to lunascout/docs/design/.
7. Create .gitignore (Python, Node, OS files, .env, .venv, __pycache__, data/raw/*, *.tif except tiny test files) and .gitattributes if useful.
8. Create a minimal README.md (project name, one-line pitch, "Work in progress", structure overview, "Use of AI" placeholder section) and a root requirements-dev.txt (pytest).
9. Add the AI-use header from CONTRACT.md section 7 to every code file you create.
10. git init, make the first commit on main, then create the branches feat/ephemeris, feat/engine, feat/api and feat/web from main.
11. If the GitHub CLI (gh) is installed and authenticated, create a PUBLIC repo named "lunascout" and push main and all branches. If not, tell me the exact commands to do it manually.

Don't write any engine, API or frontend code: other agents will do that. When done, show me the final tree and the repo URL.
