import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Example: Access environment variables
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "university_db")

# You can add more environment variables as needed

if __name__ == "__main__":
    print(f"MONGODB_URI: {MONGODB_URI}")
    print(f"DATABASE_NAME: {DATABASE_NAME}")
