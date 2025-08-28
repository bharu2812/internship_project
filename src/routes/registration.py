

from fastapi import APIRouter, Form

from fastapi.responses import JSONResponse, HTMLResponse
from db.mongodb import get_db
from models.candidate import Candidate
from pymongo import ReturnDocument


router = APIRouter()


@router.post("/api/registrations")
async def register_user(
    university_registration_number: str = Form(...),
    name: str = Form(...),
    university_name: str = Form(...),
    location: str = Form(...),
    semester: str = Form(...),
    branch: str = Form(...),
    
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
        university_name=university_name,
        location=location,
        semester=semester,
        branch=branch
    )
    candidate_data = candidate.dict()
    candidate_data["user_type"] = "candidate"
    candidate_data["candidate_id"] = candidate_id
    result = candidate_collection.insert_one(candidate_data)

    # Return simple HTML success page
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
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
