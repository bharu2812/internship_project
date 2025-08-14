from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from db.mongodb import get_db
from models.hod import HOD
import secrets
import bcrypt
from pymongo import ReturnDocument
import smtplib
from email.message import EmailMessage

router = APIRouter()
security = HTTPBasic()

# Portal Owner credentials
PORTAL_USERNAME = "portaluser@lenovo.com"
# Hashed password for "secret123"
PORTAL_HASHED_PASSWORD = bcrypt.hashpw(b"secret123", bcrypt.gensalt())

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, PORTAL_USERNAME)
    correct_password = bcrypt.checkpw(credentials.password.encode(), PORTAL_HASHED_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid Portal Owner credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

def get_next_hod_id(hod_collection):
    # Ensure the sequence tracker exists and starts at 1000
    hod_collection.update_one(
        {"_id": "sequence_tracker"},
        {"$setOnInsert": {"hod_id": 1000}},
        upsert=True
    )

    # Now increment and return the next value
    tracker = hod_collection.find_one_and_update(
        {"_id": "sequence_tracker"},
        {"$inc": {"hod_id": 1}},
        return_document=ReturnDocument.AFTER
    )
    return tracker["hod_id"]

@router.post("/api/create-hod")
async def create_hod(hod: HOD, _: HTTPBasicCredentials = Depends(authenticate)):
    hod_collection = get_db()
    try:
        query = {
            "email": hod.email,
            "university_name": hod.university_name,
            "registration_year": hod.registration_year,
            "departments": {"$in": hod.departments}
        }
        existing = hod_collection.find_one(query)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="HOD with this email is already registered for the same university, department, and registration year."
            )

        # Get next sequential HOD ID
        hod_id = get_next_hod_id(hod_collection)

        
        hod_data = hod.dict()
        hod_data["user_type"] = "hod"
        hod_data["hod_id"] = hod_id  

        result = hod_collection.insert_one(hod_data)

        # Send email to HOD after successful registration
        sender_email = "bharathisriram2001@gmail.com"
        receiver_email = hod.email
        subject = "Welcome to HOD Portal"
        body = f"Dear HOD,\n\nYour account has been created. Please set your password using the following link: http://127.0.0.1:8000/setup-password?email={hod.email}\n\nYour username: {hod.email.split('@')[0]}\n\nRegards,\nPortal Team"
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, 'pyzs anhf fgum fkch')  # Use app password
                smtp.send_message(msg)
        except Exception as e:
            print(f"Error sending email: {e}")

        return {
            "id": str(result.inserted_id),
            "hod_id": hod_id,
            "message": "Data inserted and email sent"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
