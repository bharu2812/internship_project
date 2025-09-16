from fastapi import APIRouter, Form, Request
"""
MongoDB Collections Overview:

- candidate_tests:
    Stores test metadata and the set of questions assigned to each candidate.
    Tracks the test status (e.g., "submitted") and ensures each candidate only takes the test once.
    Used for test setup, assigned questions, and status tracking.

- candidate_submissions:
    Stores the actual answers submitted by the candidate when they complete the test.
    Records which answers were chosen, how many were submitted, and the submission timestamp.
    Used for candidate's submitted answers and submission details.

This separation allows test assignment and answer submission data to be managed independently, making it easier to maintain test integrity and analyze candidate responses.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from db.mongodb import get_db, get_db_connection
from models.candidate import Candidate
from pymongo import ReturnDocument
from vector_db.qdrant import search_questions
import random
from datetime import datetime
from typing import List, Optional
import json

router = APIRouter()


from typing import List
def _tile_page(regno: str, name: str, candidate_id: int | None = None, already_submitted: bool = False):
        submit_note = "<div style='margin-top:18px;color:#27ae60;font-weight:600;'>Test already submitted.</div>" if already_submitted else ""
        disabled_attr = "disabled style='opacity:.55;cursor:not-allowed;'" if already_submitted else ""
        html = f"""
        <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Candidate Portal</title>
        <meta name='viewport' content='width=device-width,initial-scale=1.0'>
        <style>
            body{{font-family:Arial,Segoe UI,sans-serif;background:#f4f6fa;margin:0;padding:0;}}
            .wrap{{max-width:960px;margin:60px auto 80px;padding:0 24px;}}
            .hero{{text-align:center;margin-bottom:42px;}}
            .tiles{{display:flex;flex-wrap:wrap;justify-content:center;gap:38px;}}
            .tile{{flex:1 1 320px;max-width:360px;background:#fff;border-radius:22px;padding:48px 40px;box-shadow:0 8px 28px -6px rgba(0,0,0,.10),0 2px 6px rgba(0,0,0,.06);position:relative;overflow:hidden;}}
            .tile::before{{content:"";position:absolute;inset:0;background:radial-gradient(circle at 28% 32%,rgba(25,118,210,.15),transparent 70%);pointer-events:none;}}
            h1{{margin:0 0 12px;color:#2d3e50;font-size:2.1rem;}}
            p.subtitle{{margin:4px 0 28px;color:#4a5a6a;font-size:1.05rem;}}
            .take-btn{{display:inline-block;background:#1976d2;color:#fff;text-decoration:none;font-weight:600;letter-spacing:.5px;padding:20px 46px;border-radius:14px;font-size:1.25rem;box-shadow:0 4px 18px -2px rgba(25,118,210,.45);transition:.28s;}}
            .take-btn:hover{{background:#125ea2;transform:translateY(-3px);}}
            .take-btn:active{{transform:translateY(-1px);}}
            .take-btn[disabled]{{background:#9aa5af;box-shadow:none;}}
        </style></head><body>
            <div class='wrap'>
                <div class='hero'>
                    <h1>Welcome, {name}</h1>
                    <p class='subtitle'>You're registered. Start your skill assessment when ready.</p>
                </div>
                <div class='tiles'>
                    <div class='tile'>
                         <h2 style='margin:0 0 18px;font-size:1.4rem;color:#2d3e50;'>Skill Assessment Test</h2>
                         <p style='margin:0 0 30px;color:#4a5a6a;line-height:1.5;'>Answer a curated set of questions based on your selected skills. You can take it once.</p>
                         <a class='take-btn' href='/take-test?regno={regno}&name={name}' {disabled_attr}>Take Test</a>
                         {submit_note}
                    </div>
                </div>
            </div>
        </body></html>
        """
        return HTMLResponse(html)

@router.get("/candidate-portal", response_class=HTMLResponse)
async def candidate_portal(regno: str, name: str = ""):
    """Direct endpoint to show the tile page if candidate exists (skip form)."""
    db = get_db_connection()
    users = get_db()
    submissions = db["candidate_submissions"]
    tests = db["candidate_tests"]
    existing = users.find_one({"regNo": regno})
    if not existing:
        return HTMLResponse("<h2>Candidate not found. Please register.</h2>", status_code=404)
    candidate_id = existing.get("candidate_id")
    already_submitted = bool(submissions.find_one({"student_regno": regno}))
    # Ensure test doc exists
    test_doc = tests.find_one({"student_regno": regno})
    if not test_doc:
        skill_list_existing = existing.get("skills", [])
        aggregated = []
        for skill in skill_list_existing:
            for q in search_questions(skill, limit=30):
                print("q",q)
                q = dict(q); q["skill"] = skill; aggregated.append(q)
        seen_ids = set(); unique_qs = []
        for q in aggregated:
            key = q.get("id") or q.get("text")
            if key and key not in seen_ids:
                unique_qs.append(q); seen_ids.add(key)
        selected = random.sample(unique_qs, min(30, len(unique_qs))) if unique_qs else []
        tests.insert_one({
            "student_regno": regno,
            "student_name": existing.get("name", name),
            "candidate_id": candidate_id,
            "questions": selected,
            "created_at": datetime.utcnow(),
            "status": "pending"
        })
    return _tile_page(regno, existing.get("name", name), candidate_id, already_submitted)

@router.post("/api/registrations")
async def register_user(
        university_registration_number: str = Form(...),
        name: str = Form(...),
        semester: str = Form(...),
        branch: str = Form(...),
        skills: Optional[str] = Form(None),
        projects: Optional[str] = Form(None),
        achievements: Optional[str] = Form(None),
        certifications: Optional[str] = Form(None),
        email: Optional[str] = Form(None)
):
    users = get_db()  # This is your user collection
    skills_list = json.loads(skills) if skills else []
    projects_list = json.loads(projects) if projects else []

    update_fields = {
        "name": name,
        "semester": semester,
        "branch": branch,
        "skills": skills_list,
        "projects": projects_list,
        "achievements": achievements,
        "certifications": certifications,
        "email": email
    }

    # Remove None values
    update_fields = {k: v for k, v in update_fields.items() if v is not None}

    # Update the user record by registration number
    users.update_one(
        {"regNo": university_registration_number},
        {"$set": update_fields},
        upsert=True  # Creates a new record if not found
    )

    candidate_collection = get_db()
    test_collection = get_db_connection()["candidate_tests"]
    submissions_collection = get_db_connection()["candidate_submissions"]
    existing = candidate_collection.find_one({"regNo": university_registration_number})
    if existing:
        candidate_id = existing.get("candidate_id")
        test_doc = test_collection.find_one({"student_regno": university_registration_number})
        if not test_doc:
            # Generate and store questions for existing candidate (once)
            skill_list_existing = existing.get("skills", [])
            aggregated = []
            for skill in skill_list_existing:
                for q in search_questions(skill, limit=15):
                    q = dict(q); q["skill"] = skill; aggregated.append(q)
            seen_ids = set(); unique_qs = []
            for q in aggregated:
                key = q.get("id") or q.get("text")
                if key and key not in seen_ids:
                    unique_qs.append(q); seen_ids.add(key)
            selected = random.sample(unique_qs, min(30, len(unique_qs))) if unique_qs else []
            test_collection.insert_one({
                "student_regno": university_registration_number,
                "student_name": existing.get("name", name),
                "candidate_id": candidate_id,
                "questions": selected,
                "created_at": datetime.utcnow(),
                "status": "pending"
            })
        already_submitted = bool(submissions_collection.find_one({"student_regno": university_registration_number}))
        return _tile_page(university_registration_number, existing.get("name", name), candidate_id, already_submitted)

    # Get next sequential candidate ID
    candidate_collection.update_one(
        {"_id": "sequence_tracker"},
        {"$setOnInsert": {"candidate_id": 1000}},
        upsert=True
    )
    tracker = candidate_collection.find_one_and_update(
        {"_id": "sequence_tracker"},
        {"$inc": {"candidate_id": 1}},
        return_document=ReturnDocument.AFTER
    )
    candidate_id = tracker["candidate_id"]


    projects_list = json.loads(projects) if projects else []

    candidate = Candidate(
        university_registration_number=university_registration_number,
        name=name,
    # university_name and location removed
        semester=semester,
        branch=branch,
        skills=skills,
        projects=projects_list
    )
    candidate_data = candidate.dict()
    candidate_data["user_type"] = "candidate"
    candidate_data["candidate_id"] = candidate_id
    result = candidate_collection.insert_one(candidate_data)

    # Generate questions ONCE and store for later test taking
    skill_list = [s.strip() for s in skills if s.strip()]
    aggregated = []
    for skill in skill_list:
        for q in search_questions(skill, limit=15):
            q = dict(q); q["skill"] = skill; aggregated.append(q)
    seen_ids = set(); unique_qs = []
    for q in aggregated:
        key = q.get("id") or q.get("text")
        if key and key not in seen_ids:
            unique_qs.append(q); seen_ids.add(key)
    selected = random.sample(unique_qs, min(30, len(unique_qs))) if unique_qs else []
    test_collection.insert_one({
        "student_regno": university_registration_number,
        "student_name": name,
        "candidate_id": candidate_id,
        "questions": selected,
        "created_at": datetime.utcnow(),
        "status": "pending"
    })
    return _tile_page(university_registration_number, name, candidate_id)


@router.get("/api/skills-list")
def get_skills_list():
    db = get_db_connection()
    skills_collection = db["skills_list"]
    pipeline = [
        {"$unwind": "$skills"},
        {"$group": {"_id": None, "allSkills": {"$addToSet": "$skills"}}},
        {"$project": {"_id": 0, "allSkills": 1}}
    ]
    result = list(skills_collection.aggregate(pipeline))
    # Flatten to 'skills' key for frontend dropdown/checkbox logic
    skills = result[0]["allSkills"] if result and "allSkills" in result[0] else []
    return JSONResponse(content={"skills": skills})


@router.post("/api/submit-answers")
async def submit_answers(request: Request):
    form = await request.form()
    student_regno = form.get('student_regno')
    student_name = form.get('student_name')
    total = form.get('total')
    try:
        total_int = int(total)
    except Exception:
        total_int = 0
    submitted_answers = []
    for i in range(total_int):
        q_id = form.get(f'question_id_{i}')
        q_text = form.get(f'question_text_{i}')
        chosen = form.get(f'answer_{i}')
        skill = form.get(f'skill_{i}')
        difficulty = form.get(f'difficulty_{i}')
        if q_id and q_text and chosen:
            submitted_answers.append({
                'question_id': q_id,
                'question': q_text,
                'chosen_answer': chosen,
                'skill': skill,
                'difficulty_level': difficulty
            })
    db = get_db_connection()
    submissions = db['candidate_submissions']
    doc = {
        'student_regno': student_regno,
        'student_name': student_name,
        'submitted_answers': submitted_answers,
        'submitted_count': len(submitted_answers),
        'total_questions_presented': total_int,
        'submitted_at': datetime.utcnow()
    }
    submissions.insert_one(doc)
    # Mark test as completed
    db['candidate_tests'].update_one({"student_regno": student_regno}, {"$set": {"status": "submitted", "submitted_at": datetime.utcnow()}}, upsert=False)
    # Confirmation page
    # Return lightweight page that immediately shows a dialog and redirects
    html = f"""
    <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Submitting...</title>
    <meta name='viewport' content='width=device-width,initial-scale=1.0'>
    <script>
    window.addEventListener('DOMContentLoaded', function() {{
        alert('Thank you for submitting the test.');
        window.location.href = '/take-test?regno={student_regno}&name={student_name}';
    }});
    </script>
    <style>body{{font-family:Arial,Segoe UI,sans-serif;background:#f4f6fa;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}}
    .msg{{background:#fff;padding:32px 40px;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.08);text-align:center;font-size:1rem;color:#2d3e50;}}
    a{{color:#1976d2;text-decoration:none;font-weight:600;}}</style></head>
    <body>
        <div class='msg'>Processing your submission...<br><small>If you are not redirected automatically <a href='/take-test?regno={student_regno}&name={student_name}'>click here</a>.</small></div>
        <noscript><p style='text-align:center;'>Thank you for submitting the test. <a href='/take-test?regno={student_regno}&name={student_name}'>Continue</a>.</p></noscript>
    </body></html>
    """
    return HTMLResponse(html)


@router.get("/take-test", response_class=HTMLResponse)
async def take_test(regno: str, name: str = ""):
    db = get_db_connection()
    test_collection = db['candidate_tests']
    subs_collection = db['candidate_submissions']
    submission = subs_collection.find_one({"student_regno": regno})
    if submission:
        # Already submitted -> show summary page redirect option
        return _tile_page(regno, submission.get('student_name', name), submission.get('candidate_id'), already_submitted=True)
    test_doc = test_collection.find_one({"student_regno": regno})
    if not test_doc:
        return HTMLResponse("<html><body><h2>No test prepared for this registration number.</h2></body></html>", status_code=404)
    questions = test_doc.get('questions', [])
    form_parts = [
        "<h1 style='margin-top:0;'>Skill Assessment Test</h1>",
        "<form method='post' action='/api/submit-answers' style='text-align:left;'>",
        f"<input type='hidden' name='student_regno' value='{regno}'>",
        f"<input type='hidden' name='student_name' value='{test_doc.get('student_name', name)}'>",
        f"<input type='hidden' name='total' value='{len(questions)}'>",
    ]
    for idx, q in enumerate(questions):
        q_id = q.get('id') or f"auto_{idx}"
        q_text = (q.get('text') or '').replace('"','&quot;')
        opts = q.get('options') or []
        skill = q.get('skill','')
        difficulty = q.get('difficulty','')
        form_parts.append("<div style='margin-bottom:28px;padding:18px 20px;border:1px solid #e0e0e0;border-radius:10px;background:#fff;'>")
        form_parts.append(f"<p style='font-weight:600;margin:0 0 12px;'>Q{idx+1}. {q_text}</p>")
        form_parts.append(f"<input type='hidden' name='question_id_{idx}' value='{q_id}'>")
        form_parts.append(f"<input type='hidden' name='question_text_{idx}' value=\"{q_text}\">")
        form_parts.append(f"<input type='hidden' name='skill_{idx}' value='{skill}'>")
        form_parts.append(f"<input type='hidden' name='difficulty_{idx}' value='{difficulty}'>")
        if opts:
            form_parts.append("<div style='display:flex;flex-direction:column;gap:6px;'>")
            for opt in opts:
                safe_opt = str(opt).replace('"','&quot;')
                form_parts.append(
                    f"<label style='display:flex;gap:8px;align-items:center;font-weight:500;'>"
                    f"<input type='radio' name='answer_{idx}' value=\"{safe_opt}\" required> {safe_opt}</label>"
                )
            form_parts.append("</div>")
        else:
            form_parts.append(f"<textarea name='answer_{idx}' rows='2' style='width:100%;'></textarea>")
        form_parts.append("</div>")
    form_parts.append("<button type='submit' style='background:#1976d2;color:#fff;border:none;padding:12px 26px;font-size:1rem;font-weight:600;border-radius:6px;cursor:pointer;'>Submit Answers</button>")
    form_parts.append("</form>")
    html = f"""
    <!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Take Test</title><meta name='viewport' content='width=device-width,initial-scale=1.0'>
    <style>body{{font-family:Arial,sans-serif;background:#f4f6fa;margin:0;}}.wrapper{{max-width:820px;margin:50px auto 80px;background:#fff;padding:48px 56px;border-radius:18px;box-shadow:0 4px 24px rgba(0,0,0,0.10);}}h1{{color:#2d3e50;}}</style></head>
    <body><div class='wrapper'>{''.join(form_parts)}</div></body></html>
    """
    return HTMLResponse(html)
