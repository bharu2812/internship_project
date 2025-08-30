from pymongo import MongoClient

def get_db():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["internship-program"]
    return db["users"]

# New function to get a connection to the db
def get_db_connection():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["internship-program"]
    return db

def get_all_generated_questions():
    db = get_db_connection()
    collection = db["generated_questions"]
    return list(collection.find())

