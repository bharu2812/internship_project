from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasicCredentials
from routes.hod import router as hod_router, PORTAL_USERNAME, PORTAL_HASHED_PASSWORD, authenticate
import bcrypt
import uvicorn
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_400_BAD_REQUEST
from routes.hod import router as hod_router


app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(hod_router)

# Show login page on root
@app.get("/", response_class=HTMLResponse)
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Handle login form POST
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    correct_username = username == PORTAL_USERNAME
    correct_password = bcrypt.checkpw(password.encode(), PORTAL_HASHED_PASSWORD)
    if correct_username and correct_password:
        return RedirectResponse(url="/create-hod-form", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "<span style='color:#c0392b;font-weight:bold;'>Login failed: Invalid Portal Owner credentials.</span>"
        }
    )

# Show create HOD form after login
@app.get("/create-hod-form", response_class=HTMLResponse)
async def show_create_hod_form(request: Request):
    return templates.TemplateResponse("create_hod.html", {"request": request})

# Handle HOD form submission and call API
@app.post("/submit-hod")
async def submit_hod(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    contact_number: str = Form(...),
    university_name: str = Form(...),
    location: str = Form(...),
    departments: str = Form(...),
    registration_year: str = Form(...)
):
    # Prepare payload
    payload = {
        "name": name,
        "email": email,
        "contact_number": contact_number,
        "university_name": university_name,
        "location": location,
        "departments": [d.strip() for d in departments.split(",")],
        "registration_year": registration_year
    }
    # Call create_hod API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/create-hod",
            json=payload,
            auth=(PORTAL_USERNAME, "secret123")
        )
    if response.status_code == 200:
        hod_id = response.json().get('hod_id')
        return HTMLResponse(f"""
        <html>
        <head>
            <title>HOD Created</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f6fa; }}
                .success-container {{ max-width: 400px; margin: 80px auto; background: #fff; padding: 32px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
                .success-title {{ color: #2d3e50; font-size: 24px; margin-bottom: 16px; }}
                .success-id {{ color: #27ae60; font-size: 20px; margin-bottom: 24px; }}
                .back-btn {{ background: #2d3e50; color: #fff; border: none; border-radius: 4px; padding: 10px 24px; font-size: 16px; cursor: pointer; margin-top: 16px; }}
                .back-btn:hover {{ background: #1a2533; }}
            </style>
        </head>
        <body>
            <div class="success-container">
                <div style="text-align:center; margin-bottom: 24px;">
                    <a href="https://www.lenovo.com/in/en/?Redirect=False" target="_blank">
                        <img src="https://logos-world.net/wp-content/uploads/2022/07/Lenovo-Logo.png" alt="Lenovo Logo" style="height:100px;">
                    </a>
                </div>
                <div class="success-title">HOD Created Successfully!</div>
                <div class="success-id">HOD ID: {hod_id}</div>
                <form action="/create-hod-form" method="get">
                    <button class="back-btn" type="submit">Create Another HOD</button>
                </form>
            </div>
        </body>
        </html>
        """)
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