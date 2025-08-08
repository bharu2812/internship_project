# Internship Project: FastAPI + MongoDB HOD Management

This project is a FastAPI application for managing Head of Department (HOD) data, backed by MongoDB. It provides RESTful endpoints to create HOD records.

## Project Structure

```
internship_project/
├── src/
│   ├── main.py            # FastAPI application entry point
│   ├── environment.py     # Environment/configuration setup
│   ├── db/
│   │   └── mongodb.py     # MongoDB connection logic
│   ├── models/
│   │   └── hod.py         # Pydantic model for HOD
│   └── routes/
│       └── hod.py         # API routes for HOD operations
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd internship_project
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python3 -m venv internship_proj_venv
   source internship_proj_venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure MongoDB is running locally or update connection settings in `src/db/mongodb.py`.**
5. **Run the FastAPI application (Use -B for executing without creating pycache files):**
   python3 -B  src/main.py 

## Usage

Once running, access the API at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Example Endpoints

-  **POST /hod**: Add a new HOD record
   **Request Body**:
      {
         "name": "Dr. Jane Smith",
         "email": "janesmith@university.edu",
         "contact_number": "+91-9876543210",
         "university_name": "XYZ University",
         "location": "Bangalore, India",
         "departments": ["Mathematics", "Statistics"],
         "registration_year": "2025"
      }
