"""
Qdrant vector database integration for storing and searching question bank.
Uses local Qdrant instance and Sentence Transformers for embeddings.
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from pymongo import MongoClient

def get_all_generated_questions():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["internship-program"]
    collection = db["generated_questions"]
    return list(collection.find())

# Initialize Qdrant client (cloud instance)

CLOUD_URL = "https://5a1ac755-2209-4755-b240-d0e2c132b034.europe-west3-0.gcp.cloud.qdrant.io"
CLOUD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.QiGtTbcwp6w40WSMvlmKVbngshK-O7Uc-TlSWKkmcSI"
client = QdrantClient(url=CLOUD_URL, api_key=CLOUD_API_KEY, check_compatibility=False)


# Embedding model (suitable for questions)
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

COLLECTION_NAME = "question_bank"
FINAL_COLLECTION_NAME = "final_question_bank"

# Define schema for a question and create collection in Qdrant
def get_vector_dimension() -> int:
    sample = embedding_model.encode(["sample question"])[0]
    return len(sample)

def create_collection():
    if client.collection_exists(FINAL_COLLECTION_NAME):
        client.delete_collection(FINAL_COLLECTION_NAME)
    client.create_collection(
        collection_name=FINAL_COLLECTION_NAME,
        vectors_config=VectorParams(
            size=get_vector_dimension(),
            distance=Distance.COSINE
        )
    )

def add_questions(questions: List[Dict]):
    import uuid
    texts = [q.get("question") or q.get("chunk_text") for q in questions]
    embeddings = embedding_model.encode(texts)
    points = []
    for i, q in enumerate(questions):
        # Qdrant requires point IDs to be unsigned int or UUID
        mongo_id = q.get("_id")
        try:
            # Try to use as UUID if possible
            point_id = str(uuid.UUID(str(mongo_id)))
        except Exception:
            # Fallback: generate a new UUID
            point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=embeddings[i].tolist(),
            payload={
                "text": q.get("question") or q.get("chunk_text"),
                "category": q.get("category"),
                "options": q.get("options"),
                "answer": q.get("answer"),
                "difficulty": q.get("difficulty")
            }
        )
        points.append(point)
    client.upsert(collection_name=FINAL_COLLECTION_NAME, points=points)

# Fetch all questions from MongoDB and save to Qdrant
def sync_questions_from_mongo_to_qdrant():
    questions = get_all_generated_questions()
    if not questions:
        print("No questions found in MongoDB 'generated_questions' collection.")
        return
    print(f"Fetched {len(questions)} questions from MongoDB. Saving to Qdrant...")
    add_questions(questions)
    print("Questions saved to Qdrant vector DB collection 'question_bank'.")

def search_questions(skill: str, limit: int = 10) -> List[Dict]:
    """
    Search the Qdrant vector DB collection for questions related to the given skill.
    Returns a list of matching questions (dicts).
    """
    embedding = embedding_model.encode([skill])[0].tolist()
    results = client.search(
        collection_name=FINAL_COLLECTION_NAME,
        query_vector=embedding,
        limit=limit,
        with_payload=True
    )
    return [
        {
            "id": r.id,
            "score": r.score,
            "text": r.payload.get("text"),
            "category": r.payload.get("category"),
            "options": r.payload.get("options"),
            "answer": r.payload.get("answer"),
            "difficulty": r.payload.get("difficulty")
        }
        for r in results
    ]

if __name__ == "__main__":
    create_collection()
    sync_questions_from_mongo_to_qdrant()