
from fastapi import APIRouter, Body, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from csv_utils import extract_emails_from_csv, send_password_setup_email
import threading

router = APIRouter(prefix="", tags=["candidate_management"])



# ...existing code...

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Body
import os
from csv_utils import extract_emails_from_csv, send_password_setup_email
import threading

router = APIRouter(prefix="", tags=["candidate_management"])

@router.post("/delete-candidate/")
async def delete_candidate(payload: dict = Body(...)):
    email = payload.get("email")
    print(f"[DELETE DEBUG] Received email for deletion: {email}")
    if not email:
        print("[DELETE DEBUG] Missing email in payload.")
        return {"success": False, "error": "Missing email."}
    from db.mongodb import get_db
    users_collection = get_db()
    result = users_collection.delete_one({"email": email})
    print(f"[DELETE DEBUG] Deletion result: deleted_count={result.deleted_count}")
    return {"success": result.deleted_count == 1}
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Body
import os
from csv_utils import extract_emails_from_csv, send_password_setup_email
import threading

router = APIRouter(prefix="", tags=["candidate_management"])

@router.get("/candidates/")
async def get_candidates():
    from db.mongodb import get_db
    users_collection = get_db()
    candidates = list(users_collection.find({"user_type": "candidate"}, {"_id": 0}))
    return {"candidates": candidates}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/candidate-management/{username}", response_class=HTMLResponse)
async def candidate_management(request: Request, username: str):
    return templates.TemplateResponse("candidate_management.html", {"request": request, "username": username})

# CSV upload endpoint for HOD to import students and send password setup emails
@router.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    file_location = f"uploaded_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    # Read CSV and extract full candidate data
    candidates = []
    with open(file_location, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # Expect headers: Registration No, Email ID, Name, Branch, Semester
        for line in lines[1:]:
            parts = [x.strip() for x in line.strip().split(",")]
            # Always create a candidate dict with all fields, using empty string if missing
            regNo = parts[0] if len(parts) > 0 else ""
            email = parts[1] if len(parts) > 1 else ""
            name = parts[2] if len(parts) > 2 else ""
            branch = parts[3] if len(parts) > 3 else ""
            semester = parts[4] if len(parts) > 4 else ""
            if email:  # Only add if email is present
                candidates.append({
                    "regNo": regNo,
                    "email": email,
                    "name": name,
                    "branch": branch,
                    "semester": semester,
                    "email_sent": False,
                    "user_type": "candidate"
                })
    from db.mongodb import get_db
    users_collection = get_db()
    new_emails = []
    for candidate in candidates:
        # Upsert: update existing or insert new candidate
        result = users_collection.update_one(
            {"email": candidate["email"]},
            {"$set": candidate},
            upsert=True
        )
        # Only send email if this is a new candidate
        if result.upserted_id:
            new_emails.append(candidate["email"])
    return {"message": "CSV processed.", "new_emails": new_emails}

# New endpoint to send setup emails to students in the list
@router.post("/send-setup-emails/")
async def send_setup_emails(payload: dict = Body(...)):
    emails = payload.get("emails", [])
    sender_email = "bharathisriram2001@gmail.com"
    sender_password = "pyzs anhf fgum fkch"  # Use app password
    def send_emails_thread(emails):
        sent = []
        failed = []
        error_details = {}
        from db.mongodb import get_db
        users_collection = get_db()
        for email in emails:
            existing = users_collection.find_one({"email": email, "email_sent": True})
            if existing:
                continue
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
    # Start background thread for sending emails
    threading.Thread(target=send_emails_thread, args=(emails,), daemon=True).start()
    return {"status": "Email sending started in background."}

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
    candidate["user_type"] = "candidate"
    users_collection.insert_one(candidate)
    print("Candidate inserted successfully.")
    return {"success": True}
