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

CLOUD_URL = "https://9fd877c4-0453-41b5-b91e-a82e0eaf8d08.europe-west3-0.gcp.cloud.qdrant.io"
CLOUD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.q98MU98SVR6RlrAy6iqYJax3apyey6dsi3ebKqLJL-4"
client = QdrantClient(url=CLOUD_URL, api_key=CLOUD_API_KEY)


# Embedding model (suitable for questions)
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

COLLECTION_NAME = "question_bank"


# Define schema for a question and create collection in Qdrant
def get_vector_dimension() -> int:
    sample = embedding_model.encode(["sample question"])[0]
    return len(sample)

def create_collection():
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=get_vector_dimension(),
            distance=Distance.COSINE
        )
    )
    # Create indexes for filterable fields
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="category",
        field_schema="keyword"
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="skill",
        field_schema="keyword"
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="difficulty",
        field_schema="keyword"
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
        # Ensure category is not None/null
        category = q.get("category")
        skill = q.get("skill")
        if not category:
            # Try to infer from skill or set a default
            category = q.get("skill_category") or q.get("skill") or "General"
        point = PointStruct(
            id=point_id,
            vector=embeddings[i].tolist(),
            payload={
                "text": q.get("question") or q.get("chunk_text"),
                "category": category,
                "skill": skill,
                "options": q.get("options"),
                "answer": q.get("answer"),
                "difficulty": q.get("difficulty")
            }
        )
        points.append(point)
    client.upsert(collection_name=COLLECTION_NAME, points=points)

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
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=limit,
        with_payload=True
    )
    questions = [
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
    print(f"[search_questions] Found {len(questions)} questions for skill '{skill}'")
    return questions

# --- Proportional allocation and advanced search logic ---
def search_questions_by_skill_category_difficulty(skill: str, category: str, difficulty: str, limit: int = 10) -> List[Dict]:
    """
    Search Qdrant for questions matching skill, category, and difficulty.
    """
    embedding = embedding_model.encode([skill])[0].tolist()
    print(f"[search_questions_by_skill_category_difficulty] Searching for skill: {skill}, category: {category}, difficulty: {difficulty}, limit: {limit}")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=limit,
        with_payload=True,
        query_filter={
            "must": [
                {"key": "category", "match": {"value": category}},
                {"key": "difficulty", "match": {"value": difficulty}}
            ]
        }
    )
    questions = [
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
    print(f"[search_questions_by_skill_category_difficulty] Found {len(questions)} questions for skill '{skill}', category '{category}', difficulty '{difficulty}'")
    return questions

def allocate_and_retrieve_questions(selected_categories_skills: Dict[str, List[str]], total_questions: int, difficulty_ratios: Dict[str, float] = None) -> List[Dict]:
    """
    selected_categories_skills: dict of {category: [skills]}
    total_questions: total number of questions to allocate
    difficulty_ratios: dict of {difficulty: ratio}, e.g. {"Beginner": 0.4, "Intermediate": 0.4, "Advanced": 0.2}
    Returns: list of questions allocated as per logic
    """
    import math
    print(f"[allocate_and_retrieve_questions] Input: {selected_categories_skills}, total_questions: {total_questions}, difficulty_ratios: {difficulty_ratios}")
    if not difficulty_ratios:
        difficulty_ratios = {"Beginner": 0.4, "Intermediate": 0.4, "Advanced": 0.2}

    # Step 1: Count total skills
    total_skills = sum(len(skills) for skills in selected_categories_skills.values())
    print(f"[allocate_and_retrieve_questions] Total skills: {total_skills}")
    if total_skills == 0:
        print("[allocate_and_retrieve_questions] No skills provided, returning empty list.")
        return []

    # Step 2: Allocate questions per category
    category_questions = {}
    for category, skills in selected_categories_skills.items():
        weight = len(skills) / total_skills
        category_questions[category] = math.floor(total_questions * weight)
    print(f"[allocate_and_retrieve_questions] category_questions: {category_questions}")

    # Adjust for rounding errors to ensure total matches
    diff = total_questions - sum(category_questions.values())
    if diff > 0:
        # Add remaining questions to categories with most skills
        sorted_cats = sorted(category_questions.items(), key=lambda x: -len(selected_categories_skills[x[0]]))
        for i in range(diff):
            category_questions[sorted_cats[i % len(sorted_cats)][0]] += 1
    print(f"[allocate_and_retrieve_questions] category_questions after rounding: {category_questions}")

    # Step 3: Divide questions among skills within each category
    skill_questions = {}
    for category, skills in selected_categories_skills.items():
        num_questions = category_questions[category]
        if not skills:
            continue
        per_skill = math.floor(num_questions / len(skills))
        skill_questions.update({(category, skill): per_skill for skill in skills})
        # Distribute any remainder
        remainder = num_questions - per_skill * len(skills)
        for i in range(remainder):
            skill_questions[(category, skills[i % len(skills)])] += 1

    # Step 4: Divide skill questions by difficulty
    final_questions = []
    for (category, skill), num_q in skill_questions.items():
        for difficulty, ratio in difficulty_ratios.items():
            num_diff_q = math.floor(num_q * ratio)
            # Distribute any remainder to Beginner first
            if difficulty == "Beginner":
                num_diff_q += num_q - sum(math.floor(num_q * r) for r in difficulty_ratios.values())
            if num_diff_q > 0:
                results = search_questions_by_skill_category_difficulty(skill, category, difficulty, num_diff_q)
                print(f"[allocate_and_retrieve_questions] Got {len(results)} questions for skill '{skill}', category '{category}', difficulty '{difficulty}'")
                final_questions.extend(results)
    print(f"[allocate_and_retrieve_questions] Returning {len(final_questions)} total questions.")
    return final_questions

if __name__ == "__main__":
    create_collection()
    sync_questions_from_mongo_to_qdrant()