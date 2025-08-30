from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, HTMLResponse
from db.mongodb import get_db, get_db_connection
from models.candidate import Candidate
from pymongo import ReturnDocument
from vector_db.qdrant import search_questions
import random

router = APIRouter()


from typing import List
@router.post("/api/registrations")
async def register_user(
    university_registration_number: str = Form(...),
    name: str = Form(...),
    # university_name and location removed
    semester: str = Form(...),
    branch: str = Form(...),
    skills: List[str] = Form(...),
):
    candidate_collection = get_db()
    # Check for duplicate registration
    existing = candidate_collection.find_one({"university_registration_number": university_registration_number})
    if existing:
        return JSONResponse(status_code=400, content={"error": "Duplicate university registration number."})

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


    candidate = Candidate(
        university_registration_number=university_registration_number,
        name=name,
    # university_name and location removed
        semester=semester,
        branch=branch,
        skills=skills
    )
    candidate_data = candidate.dict()
    candidate_data["user_type"] = "candidate"
    candidate_data["candidate_id"] = candidate_id
    result = candidate_collection.insert_one(candidate_data)

    # --- New logic: Search Qdrant for questions based on skills ---
    # skills is now always a list
    skill_list = [s.strip() for s in skills if s.strip()]
    print(f"Skill_list:{skill_list}")
    all_results = []
    for skill in skill_list:
        results = search_questions(skill, limit=15)
        all_results.extend(results)
    print(f"all_results:{all_results}")
    # Remove duplicates by question id/text
    seen = set()
    unique_results = []
    for q in all_results:
        key = q.get("id") or q.get("text")
        if key and key not in seen:
            unique_results.append(q)
            seen.add(key)
    # Pick 9 random questions
    selected_questions = random.sample(unique_results, min(9, len(unique_results))) if unique_results else []
    print(f"selected_questions:{selected_questions}")
    # You can now store or return selected_questions as needed
    # For demo, add to HTML response
    questions_html = ""
    if selected_questions:
        questions_html += "<h2>Recommended Questions:</h2><ul>"
        for q in selected_questions:
            questions_html += f"<li>{q.get('text')}</li>"
        questions_html += "</ul>"

    print(f"Questions HTML: {questions_html}")
    html_content = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <title>Registration Successful</title>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f4f6fa; }}
            .container {{ max-width: 500px; margin: 80px auto; background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
            h1 {{ color: #2d3e50; }}
            p {{ color: #4a5a6a; font-size: 18px; }}
            .candidate-id {{ font-weight: bold; color: #1a2533; }}
        </style>
    </head>
    <body>
        <div class='container'>
            <h1>Registration Successful!</h1>
            <p>Your registration has been completed.</p>
            <p>Your Candidate ID is: <span class='candidate-id'>{candidate_id}</span></p>
            <p>Thank you for registering for the Internship Program.</p>
            {questions_html}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


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
