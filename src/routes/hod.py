
from fastapi import APIRouter, HTTPException
from db.mongodb import get_db
from models.hod import HOD

router = APIRouter()

@router.post("/api/create-hod")
async def create_hod(hod: HOD):
    hod_collection = get_db()
    try:
        # Check for existing HOD with same email, university_name, registration_year, and any overlapping department
        query = {
            "email": hod.email,
            "university_name": hod.university_name,
            "registration_year": hod.registration_year,
            "departments": {"$in": hod.departments}
        }
        existing = hod_collection.find_one(query)
        if existing:
            raise HTTPException(status_code=400, detail="HOD with this email is already registered for the same university, department, and registration year.")
        result = hod_collection.insert_one(hod.dict())
        return {"id": str(result.inserted_id), "message": "Data inserted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))