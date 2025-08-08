# # from fastapi import APIRouter, Depends, HTTPException, status
# # from fastapi.security import HTTPBasic, HTTPBasicCredentials
# # from db.mongodb import get_db
# # from models.hod import HOD
# # import secrets
# # import bcrypt

# # router = APIRouter()
# # security = HTTPBasic()

# # # Portal Owner credentials
# # PORTAL_USERNAME = "rsingh57@lenovo.com"
# # # Hashed password for "secret123"
# # PORTAL_HASHED_PASSWORD = bcrypt.hashpw(b"secret123", bcrypt.gensalt())

# # def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
# #     correct_username = secrets.compare_digest(credentials.username, PORTAL_USERNAME)
# #     correct_password = bcrypt.checkpw(credentials.password.encode(), PORTAL_HASHED_PASSWORD)

# #     if not (correct_username and correct_password):
# #         raise HTTPException(
# #             status_code=status.HTTP_401_UNAUTHORIZED,
# #             detail="Unauthorized: Invalid Portal Owner credentials.",
# #             headers={"WWW-Authenticate": "Basic"},
# #         )

# # @router.post("/api/create-hod")
# # async def create_hod(hod: HOD, _: HTTPBasicCredentials = Depends(authenticate)):
# #     hod_collection = get_db()
# #     try:
# #         query = {
# #             "email": hod.email,
# #             "university_name": hod.university_name,
# #             "registration_year": hod.registration_year,
# #             "departments": {"$in": hod.departments}
# #         }
# #         existing = hod_collection.find_one(query)
# #         if existing:
# #             raise HTTPException(
# #                 status_code=400,
# #                 detail="HOD with this email is already registered for the same university, department, and registration year."
# #             )
# #         result = hod_collection.insert_one(hod.dict())
# #         return {"id": str(result.inserted_id), "message": "Data inserted"}
# #     except HTTPException:
# #         raise
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))

# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import HTTPBasic, HTTPBasicCredentials
# from db.mongodb import get_db
# from models.hod import HOD
# import secrets
# import bcrypt
# from pymongo import ReturnDocument

# router = APIRouter()
# security = HTTPBasic()

# # Portal Owner credentials
# PORTAL_USERNAME = "rsingh57@lenovo.com"
# # Hashed password for "secret123"
# PORTAL_HASHED_PASSWORD = bcrypt.hashpw(b"secret123", bcrypt.gensalt())

# def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
#     correct_username = secrets.compare_digest(credentials.username, PORTAL_USERNAME)
#     correct_password = bcrypt.checkpw(credentials.password.encode(), PORTAL_HASHED_PASSWORD)

#     if not (correct_username and correct_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Unauthorized: Invalid Portal Owner credentials.",
#             headers={"WWW-Authenticate": "Basic"},
#         )

# def get_next_hod_id(hod_collection):
#     # Ensure the sequence tracker exists and starts at 1000
#     hod_collection.update_one(
#         {"_id": "sequence_tracker"},
#         {"$setOnInsert": {"hod_id": 1000}},
#         upsert=True
#     )

#     # Now increment and return the next value
#     tracker = hod_collection.find_one_and_update(
#         {"_id": "sequence_tracker"},
#         {"$inc": {"hod_id": 1}},
#         return_document=ReturnDocument.AFTER
#     )
#     return tracker["hod_id"]


# @router.post("/api/create-hod")
# async def create_hod(hod: HOD, _: HTTPBasicCredentials = Depends(authenticate)):
#     hod_collection = get_db()
#     try:
#         query = {
#             "email": hod.email,
#             "university_name": hod.university_name,
#             "registration_year": hod.registration_year,
#             "departments": {"$in": hod.departments}
#         }
#         existing = hod_collection.find_one(query)
#         if existing:
#             raise HTTPException(
#                 status_code=400,
#                 detail="HOD with this email is already registered for the same university, department, and registration year."
#             )

#         # Get next sequential HOD ID
#         hod_id = get_next_hod_id(hod_collection)

#         # Prepare HOD data with custom ID
#         hod_data = hod.dict()
#         hod_data["user_type"] = "hod"
#         hod_data["hod_id"] = hod_id
#         hod_data["_id"] = hod_id
#         result = hod_collection.insert_one(hod_data)
#         return {
#             "id": hod_id,
#             "message": "Data inserted"
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from db.mongodb import get_db
from models.hod import HOD
import secrets
import bcrypt
from pymongo import ReturnDocument

router = APIRouter()
security = HTTPBasic()

# Portal Owner credentials
PORTAL_USERNAME = "rsingh57@lenovo.com"
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

        # Prepare HOD data with custom ID
        hod_data = hod.dict()
        hod_data["user_type"] = "hod"
        hod_data["hod_id"] = hod_id  # Custom field, not MongoDB _id

        result = hod_collection.insert_one(hod_data)
        return {
            "id": str(result.inserted_id),  # MongoDB's auto-generated _id
            "hod_id": hod_id,
            "message": "Data inserted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
