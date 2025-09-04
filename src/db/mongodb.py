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

# ...existing code...

def save_titles_to_mongodb(titles):
    db = get_db_connection()
    collection = db["ppt_titles"]
    # Optionally clear previous titles
    collection.delete_many({})
    # Insert each title as a document
    docs = [{"title": t} for t in titles]
    collection.insert_many(docs)
    return len(docs)
# ...existing code...