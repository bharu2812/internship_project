# FastAPI MongoDB Application

This project is a simple FastAPI application that allows users to manage HOD (Head of Department) data and store it in a MongoDB database. 

## Project Structure

```
fastapi-mongodb-app
├── src
│   ├── main.py          # Entry point of the FastAPI application
│   ├── models
│   │   └── hod.py       # Pydantic model for HOD data
│   ├── routes
│   │   └── hod.py       # API routes for HOD-related requests
│   └── db
│       └── mongodb.py    # MongoDB connection setup
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd fastapi-mongodb-app
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MongoDB:**
   Ensure that you have MongoDB installed and running on your local machine. You can use MongoDB Compass to visualize your database.

5. **Run the application:**
   ```bash
   uvicorn src.main:app --reload
   ```

## Usage

Once the application is running, you can access the API at `http://127.0.0.1:8000`.

### Endpoints

- **POST /hod**
  - Description: Add a new HOD entry.
  - Request Body:
    ```json
    {
      "name": "Dr. John Doe",
      "email": "johndoe@university.edu",
      "contact_number": "+91-9876543210",
      "university_name": "ABC University",
      "location": "New Delhi, India",
      "departments": ["Computer Science", "Data Science"],
      "registration_year": "2025",
      "student_registration_numbers": [
        "ABC123456",
        "ABC123457",
        "ABC123458"
      ]
    }
    ```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.