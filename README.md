# Internship Program Portal (FastAPI + MongoDB + Qdrant)

Portal for:
- Portal Owner (creates & manages HODs)
- HOD (manages candidates, triggers password setup emails)
- Candidates (register with skills; system recommends questions via vector similarity)

Stack: FastAPI, MongoDB, Qdrant (vector search), Sentence-Transformers, Jinja2 templates, SMTP (email), local LLM helper scripts (Ollama optional).

---

## Project Structure

```
internship_project/
├── docker-compose.yml          (present, not required for Qdrant currently)
├── requirements.txt
├── src/
│   ├── main.py
│   ├── csv_utils.py
│   ├── db/
│   │   └── mongodb.py
│   ├── models/
│   │   ├── hod.py
│   │   └── candidate.py
│   ├── routes/
│   │   ├── hod.py
│   │   ├── registration.py
│   │   └── candidate_management.py
│   ├── ai-models/
│   │   ├── generate_skills.py
│   │   └── generate_questionarrie.py
│   ├── vector_db/
│   │   └── qdrant.py
│   └── templates/
│       ├── login.html
│       ├── dashboard.html
│       ├── create_hod.html
│       ├── candidate_management.html
│       ├── registration.html
│       ├── registration_success.html
│       ├── candidate_edit_form.html
│       ├── setup_password.html
│       └── main.html
```

---

## Prerequisites

- Python 3.11.9 (download: https://www.python.org/downloads/release/python-3119/)
- MongoDB local (default: mongodb://127.0.0.1:27017)
- Qdrant running locally (manual start, NOT docker compose)
- (Optional) Ollama local for generation scripts
- SMTP account (Gmail app password etc.)

---

## Install (Windows PowerShell)

```powershell
git clone <repository-url>
cd internship_project

py -3.11 -m venv proj_venv
proj_venv\Scripts\activate

pip install -r requirements.txt
```

---

## Qdrant (Manual, No Docker Compose)

Options:

1. Local binary (Windows):
   - Download latest release: https://github.com/qdrant/qdrant/releases
   - Unzip, place qdrant.exe somewhere (e.g. tools\qdrant\)
   - Start:
     ```powershell
     cd tools\qdrant
     .\qdrant.exe
     ```
   - Default REST endpoint: http://127.0.0.1:6333

2. Cloud:
   - Create a free cluster at https://qdrant.tech/
   - Update qdrant.py with the cloud URL + API key (currently hardcoded values may need editing).

Confirm availability:
http://127.0.0.1:6333/collections

---

## Run Application

```powershell
# From repo root (venv active)
python -B src\main.py
```

Open:
http://127.0.0.1:8000/login

Interactive API docs (JSON endpoints only):
http://127.0.0.1:8000/docs

---

## Data Generation Workflow

1. Generate categorized skills (Mongo collection: skills_list):
   ```powershell
   python -m src.ai-models.generate_skills
   ```
2. Generate MCQs (Mongo collection: generated_questions):
   ```powershell
   python -m src.ai-models.generate_questionarrie
   ```
3. Embed & push questions into Qdrant (collection: question_bank):
   ```powershell
   python -m src.vector_db.qdrant
   ```

---

## Roles & Flow

- Portal Owner (hardcoded demo)
  - Username: portaluser@lenovo.com
  - Password: secret f123
- Creates HOD → email sent with setup link
- HOD sets password → logs in → manages candidates & triggers candidate setup emails
- Candidates register via form (skills → question recommendations)

---

## Candidate Registration & Recommendations

POST /api/registrations (HTML form):
- Saves candidate with sequential candidate_id
- For each selected skill: vector similarity search (top 15 per skill)
- Deduplicates, randomly selects up to 9 questions
- Displays on success page

Embedding model: sentence-transformers/all-MiniLM-L6-v2  
Stored Qdrant payload: text, category, options, answer, difficulty

---

## Selected Endpoints

HOD & Portal:
- POST /api/create-hod
- GET /create-hod-form
- POST /submit-hod
- POST /delete-hod
- GET /dashboard

Auth & Password:
- GET /login
- POST /login
- GET /setup-password
- POST /setup-password
- GET /check-username-unique

Candidate Management:
- GET /candidate-management/{username}
- GET /candidates/
- POST /upload-csv/
- POST /send-setup-emails/
- POST /add-candidate/
- POST /delete-candidate/
- GET /check-candidate-duplicate

Registration & Skills:
- GET /register/{username}
- POST /api/registrations
- GET /api/skills-list

Offline Scripts:
- ai-models/generate_skills.py
- ai-models/generate_questionarrie.py
- vector_db/qdrant.py

---

## Sequence Tracking

Incremental IDs (start 1001) maintained via sequence tracker docs for HODs and candidates. On HOD deletion tracker recalculates max.

---

## Email Usage

SMTP (port 465 SSL) for:
- HOD creation/setup link
- Candidate setup batch emails (background thread)

(Plaintext credentials currently in code — refactor before any deployment.)

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Skills dropdown empty | skills_list not generated | Run generate_skills.py |
| No recommendations | generated_questions empty or Qdrant not loaded | Run generation + qdrant script |
| Qdrant connection error | Service not started | Start qdrant.exe |
| Emails failing | Bad SMTP/app password | Verify credentials |
| Duplicate IDs | Sequence tracker drift | Recompute max, adjust tracker doc |

---

## Quick Commands

```powershell
# Run app
python -B src\main.py

# Full regenerate pipeline
python -m src.ai-models.generate_skills
python -m src.ai-models.generate_questionarrie
python -m src.vector_db.qdrant
```

---

## Hardening (Planned)

- Externalize SMTP & Qdrant credentials
- Add proper auth (JWT / session store)
- CSV validation & rate limiting
- Structured logging & error handling

---

## Disclaimer

Demo credentials and keys are hardcoded. Remove or externalize before production.
