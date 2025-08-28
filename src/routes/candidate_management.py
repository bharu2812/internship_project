from fastapi import APIRouter
# Get all candidates for frontend table

# ...existing code...

router = APIRouter(prefix="", tags=["candidate_management"])

# ...existing code...
from fastapi import APIRouter
@router.get("/candidates/")
async def get_candidates():
    from db.mongodb import get_db
    users_collection = get_db()
    candidates = list(users_collection.find({}, {"_id": 0}))
    return {"candidates": candidates}
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Body
import os
from csv_utils import extract_emails_from_csv, send_password_setup_email

router = APIRouter(prefix="", tags=["candidate_management"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/candidate-management", response_class=HTMLResponse)
async def candidate_management(request: Request):
    return templates.TemplateResponse("candidate_management.html", {"request": request})

# CSV upload endpoint for HOD to import students and send password setup emails
@router.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    file_location = f"uploaded_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    emails = extract_emails_from_csv(file_location)
    from db.mongodb import get_db
    users_collection = get_db()
    new_emails = []
    for email in emails:
        if not users_collection.find_one({"email": email}):
            users_collection.insert_one({"email": email, "email_sent": False})
            new_emails.append(email)
    return {"message": "CSV processed.", "new_emails": new_emails}

# New endpoint to send setup emails to students in the list
@router.post("/send-setup-emails/")
async def send_setup_emails(payload: dict = Body(...)):
    emails = payload.get("emails", [])
    sender_email = "bharathisriram2001@gmail.com"
    sender_password = "pyzs anhf fgum fkch"  # Use app password
    sent = []
    failed = []
    error_details = {}
    from db.mongodb import get_db
    users_collection = get_db()
    for email in emails:
        # Only send if not already sent
        existing = users_collection.find_one({"email": email, "email_sent": True})
        if existing:
            continue  # Skip already sent
        setup_url = f"http://127.0.0.1:8000/setup-password?email={email}"
        try:
            result = send_password_setup_email(email, setup_url, sender_email, sender_password)
            if result:
                sent.append(email)
                users_collection.update_one(
                    {"email": email},
                    {"$set": {"email_sent": True}},
                    upsert=True
                )
            else:
                failed.append(email)
                error_details[email] = f"Email sending failed (see backend logs)"
        except Exception as e:
            failed.append(email)
            error_details[email] = str(e)
            print(f"Error sending to {email}: {e}")
    print(f"Send email summary: Sent={sent}, Failed={failed}, Details={error_details}")
    return {
        "emails_sent": sent,
        "emails_failed": failed,
        "error_details": error_details
    }

# @router.get("/candidates/")
# async def get_candidates():
#     from db.mongodb import get_db
#     users_collection = get_db()
#     candidates = list(users_collection.find({}, {"_id": 0}))
#     return {"candidates": candidates}


@router.post("/add-candidate/")
async def add_candidate(candidate: dict = Body(...)):
    from db.mongodb import get_db
    users_collection = get_db()
    regNo = candidate.get("regNo")
    email = candidate.get("email")
    print(f"Trying to add candidate: regNo={regNo}, email={email}")
    if not regNo or not email:
        print("Missing registration number or email.")
        return {"success": False, "error": "Missing registration number or email."}
    # Check for duplicates
    duplicate = users_collection.find_one({"$or": [{"email": email}, {"regNo": regNo}]})
    print(f"Duplicate check result: {duplicate}")
    if duplicate:
        print("Duplicate candidate found.")
        return {"success": False, "error": "Duplicate candidate (email or registration number already exists)."}
    users_collection.insert_one(candidate)
    print("Candidate inserted successfully.")
    return {"success": True}
