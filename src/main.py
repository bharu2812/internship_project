
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
from fastapi.security import HTTPBasicCredentials
from routes.hod import router as hod_router, PORTAL_USERNAME, PORTAL_HASHED_PASSWORD, authenticate
from routes.registration import router as registration_router
from routes.candidate_management import router as candidate_management_router
import bcrypt
import uvicorn
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_400_BAD_REQUEST
from routes.hod import router as hod_router
from bson import ObjectId


# Only one app = FastAPI() and template setup at the top
app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Register /delete-hod endpoint directly with FastAPI (not via router)
@app.post("/delete-hod")
async def delete_hod(hod_id: str = Form(...)):
    from db.mongodb import get_db
    hod_collection = get_db()
    print(f"[DEBUG] Received hod_id for delete: {hod_id}")
    try:
        result = hod_collection.delete_one({"_id": ObjectId(hod_id)})
        print(f"[DEBUG] Delete result: deleted_count={result.deleted_count}")
        # After deletion, update sequence_tracker to max hod_id in collection
        if result.deleted_count == 1:
            max_hod = hod_collection.find_one(
                {"user_type": "hod"},
                sort=[("hod_id", -1)]
            )
            new_seq = max_hod["hod_id"] if max_hod and "hod_id" in max_hod else 1000
            hod_collection.update_one(
                {"_id": "sequence_tracker"},
                {"$set": {"hod_id": new_seq}}
            )
        return {"success": result.deleted_count == 1}
    except Exception as e:
        print(f"[DEBUG] Exception during delete: {e}")
        return {"success": False, "error": str(e)}

# Register /delete-candidate endpoint directly with FastAPI (not via router)
from fastapi import Body
@app.post("/delete-candidate/")
async def delete_candidate_root(payload: dict = Body(...)):
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


# In-memory HOD user store for demo (replace with DB in production)
HOD_USERS = {}

# Registration Page (GET) with prefill support
@app.get("/register", response_class=HTMLResponse)
async def show_registration_form(
    request: Request,
    regNo: str = "",
    email: str = "",
    name: str = "",
    branch: str = "",
    semester: str = "",
    university_name: str = "",
    location: str = "",
    projects: str = "",
    # removed skills/certifications/achievements
    edit: str = "0"
):
    return templates.TemplateResponse(
        "registration.html",
        {
            "request": request,
            "regNo": regNo,
            "email": email,
            "name": name,
            "branch": branch,
            "semester": semester,
            "university_name": university_name,
            "location": location,
            "projects": projects,
            "edit": edit
        }
    )

# Password Setup Page (GET)

@app.get("/setup-password", response_class=HTMLResponse)
async def setup_password_form(request: Request, email: str = ""):
    username = ""
    return templates.TemplateResponse("setup_password.html", {"request": request, "username": username, "email": email})


# Password Setup Page (POST)

@app.post("/setup-password", response_class=HTMLResponse)
async def setup_password_submit(request: Request, username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), email: str = Form("") ):
    if password != confirm_password:
        return templates.TemplateResponse("setup_password.html", {"request": request, "username": username, "email": email, "error": "Passwords do not match."})
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    # Store username and hashed password in MongoDB securely
    from db.mongodb import get_db
    hod_collection = get_db()
    # Check if username is already taken
    existing_user = hod_collection.find_one({"username": username})
    if existing_user:
        return templates.TemplateResponse("setup_password.html", {"request": request, "username": username, "email": email, "error": "Username is already taken. Please choose another."})

    # Update HOD record with username and password (find by email)
    result = hod_collection.update_one(
        {"email": email},
        {"$set": {"username": username, "password": hashed_pw.decode("utf-8")}},
        upsert=False
    )
    if result.matched_count == 0:
        return templates.TemplateResponse("setup_password.html", {"request": request, "username": username, "email": email, "error": "No HOD record found for this email. Please contact admin."})

    # Show confirmation and login URL at the bottom of the same page
    login_url = "/login"
    return templates.TemplateResponse(
        "setup_password.html",
        {
            "request": request,
            "username": username,
            "email": email,
            "success": True,
            "login_url": login_url
        }
    )

# Check if username is unique (for live validation)
from fastapi import Query
@app.get("/check-username-unique")
async def check_username_unique(username: str = Query(...)):
    from db.mongodb import get_db
    hod_collection = get_db()
    exists = hod_collection.find_one({"username": username})
    return {"unique": not bool(exists)}

# Check for candidate duplicate (manual entry)
@app.get("/check-candidate-duplicate")
async def check_candidate_duplicate(email: str = Query(...), regNo: str = Query(...)):
    from db.mongodb import get_db
    users_collection = get_db()
    duplicate = users_collection.find_one({"$or": [{"email": email}, {"regNo": regNo}]})
    return {"duplicate": bool(duplicate)}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(hod_router)
app.include_router(registration_router)
print("Including candidate_management_router at root prefix for /candidate-management route")
app.include_router(candidate_management_router)

    # Show login page at /login
@app.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Handle login form POST (for both Portal Owner and HOD)
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Portal Owner login
    if username == PORTAL_USERNAME and bcrypt.checkpw(password.encode(), PORTAL_HASHED_PASSWORD):
        return RedirectResponse(url="/dashboard", status_code=303)

    # HOD login (validate from MongoDB)
    from db.mongodb import get_db
    hod_collection = get_db()
    # Find HOD by username field
    hod_user = hod_collection.find_one({"username": username})
    if hod_user and "password" in hod_user:
        db_hashed_pw = hod_user["password"].encode("utf-8")
        if bcrypt.checkpw(password.encode(), db_hashed_pw):
            return RedirectResponse(url="/candidate-management", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "<span style='color:#c0392b;font-weight:bold;'>Login failed: Invalid credentials.</span>"
        }
    )

# Main Portal for HOD
@app.get("/main", response_class=HTMLResponse)
async def show_main_portal(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

# Dashboard for Portal Owner (shows HOD table)
@app.get("/dashboard", response_class=HTMLResponse)
async def show_dashboard(request: Request):
    from db.mongodb import get_db
    hod_collection = get_db()
    hods = list(hod_collection.find({"user_type": "hod"}))
    # Convert ObjectId to string for Jinja
    for hod in hods:
        hod["_id"] = str(hod["_id"])
    return templates.TemplateResponse("dashboard.html", {"request": request, "hods": hods})

# Show create HOD form after login
@app.get("/create-hod-form", response_class=HTMLResponse)
async def show_create_hod_form(request: Request, hod_id: str = None):
    from datetime import datetime
    hod_data = None
    if hod_id:
        from db.mongodb import get_db
        hod_collection = get_db()
        from bson import ObjectId
        hod = hod_collection.find_one({"_id": ObjectId(hod_id)})
        if hod:
            hod_data = {
                "_id": str(hod["_id"]),
                "name": hod.get("name", ""),
                "email": hod.get("email", ""),
                "contact_number": hod.get("contact_number", ""),
                "university_name": hod.get("university_name", ""),
                "departments": ", ".join(hod.get("departments", [])) if isinstance(hod.get("departments"), list) else hod.get("departments", ""),
                "registration_year": hod.get("registration_year", "")
            }
    current_year = datetime.now().year
    return templates.TemplateResponse("create_hod.html", {"request": request, "hod": hod_data, "current_year": current_year})

# Handle HOD form submission and call API
@app.post("/submit-hod")
async def submit_hod(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    contact_number: str = Form(...),
    university_name: str = Form(...),
    departments: str = Form(...),
    registration_year: str = Form(...),
    hod_id: str = Form(None)
):
    from db.mongodb import get_db
    from bson import ObjectId
    hod_collection = get_db()
    departments_list = [d.strip() for d in departments.split(",")]
    if len(contact_number) != 10 or not contact_number.isdigit():
        return templates.TemplateResponse(
            "create_hod.html",
            {
                "request": request,
                "hod": {
                    "name": name,
                    "email": email,
                    "contact_number": contact_number,
                    "university_name": university_name,
                    "departments": departments,
                    "registration_year": registration_year
                },
                "error": "Contact Number must be exactly 10 digits."
            }
        )
    if hod_id:
        # Update existing HOD
        update_result = hod_collection.update_one(
            {"_id": ObjectId(hod_id)},
            {"$set": {
                "name": name,
                "email": email,
                "contact_number": contact_number,
                "university_name": university_name,
                "departments": departments_list,
                "registration_year": registration_year
            }}
        )
        return RedirectResponse(url="/dashboard", status_code=303)
    else:
        # Check for duplicate email before creating
        existing = hod_collection.find_one({"email": email})
        if existing:
            # Show a clear error message for duplicate HOD
            return templates.TemplateResponse(
                "create_hod.html",
                {
                    "request": request,
                    "hod": {
                        "name": name,
                        "email": email,
                        "contact_number": contact_number,
                        "university_name": university_name,
                        "departments": departments,
                        "registration_year": registration_year
                    },
                    "error": "Duplicate HOD: A record with this email already exists."
                }
            )
        # Prepare payload for create
        payload = {
            "name": name,
            "email": email,
            "contact_number": contact_number,
            "university_name": university_name,
            "departments": departments_list,
            "registration_year": registration_year
        }
        # Call create_hod API
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/api/create-hod",
                json=payload,
                auth=(PORTAL_USERNAME, "secret123")
            )
        if response.status_code == 200:
            return RedirectResponse(url="/dashboard", status_code=303)
        return HTMLResponse(f"""
            <html>
            <head>
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; background: #f4f6fa; }}
                    .error-container {{ max-width: 400px; margin: 80px auto; background: #fff; padding: 32px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
                    .error-title {{ color: #c0392b; font-size: 24px; margin-bottom: 16px; }}
                    .error-msg {{ color: #4a5a6a; font-size: 18px; margin-bottom: 24px; }}
                    .back-btn {{ background: #2d3e50; color: #fff; border: none; border-radius: 4px; padding: 10px 24px; font-size: 16px; cursor: pointer; margin-top: 16px; }}
                    .back-btn:hover {{ background: #1a2533; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div style="text-align:center; margin-bottom: 24px;">
                        <a href="https://www.lenovo.com/in/en/?Redirect=False" target="_blank">
                            <img src="https://logos-world.net/wp-content/uploads/2022/07/Lenovo-Logo.png" alt="Lenovo Logo" style="height:100px;">
                        </a>
                    </div>
                    <div class="error-title">Error Creating HOD</div>
                    <div class="error-msg">{response.text}</div>
                    <form action="/create-hod-form" method="get">
                        <button class="back-btn" type="submit">Back to Form</button>
                    </form>
                </div>
            </body>
            </html>
            """)

# Custom handler for missing fields
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    missing_fields = [
        err["loc"][-1]
        for err in errors
        if err["type"] == "missing"
    ]
    if missing_fields:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": f"You didn't pass the required attribute: {', '.join(missing_fields)}"}
        )
    # fallback to default error if not missing field
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": errors})
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)