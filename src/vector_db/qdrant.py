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

CLOUD_URL = "https://06feefe4-78c9-4566-830c-0c0671845e4b.europe-west3-0.gcp.cloud.qdrant.io"
CLOUD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.2JpIGhC43YHL3dzl7gs3AowMkwXG9w4BDgXlgoLpN7M"
client = QdrantClient(url=CLOUD_URL, api_key=CLOUD_API_KEY, check_compatibility=False)


# Embedding model (suitable for questions)
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

COLLECTION_NAME = "question_bank"

def is_valid_question(question: Dict) -> bool:
    """
    Check if a question has valid options (not generic placeholders like 'Option 1', 'Option 2', etc.)
    Returns False if any option contains generic placeholder text.
    """
    options = question.get("options", [])
    if not options or not isinstance(options, list):
        return False
    
    # Check for generic option placeholders
    invalid_patterns = [
        "option 1", "option 2", "option 3", "option 4",
        "option a", "option b", "option c", "option d",
        "choice 1", "choice 2", "choice 3", "choice 4"
    ]
    
    for option in options:
        if isinstance(option, str):
            option_lower = option.lower().strip()
            # Check if the option is exactly one of the invalid patterns
            if option_lower in invalid_patterns:
                return False
            # Also check if it starts with these patterns (like "Option 1:")
            for pattern in invalid_patterns:
                if option_lower.startswith(pattern):
                    return False
    
    return True


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
def search_questions_by_skill_category_difficulty(skill: str, category: str, difficulty: str, limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    Search Qdrant for questions matching skill, category, and difficulty.
    """
    embedding = embedding_model.encode([skill])[0].tolist()
    print(f"[search_questions_by_skill_category_difficulty] Searching for skill: {skill}, category: {category}, difficulty: {difficulty}, limit: {limit}, offset: {offset}")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=limit + offset,  # Fetch more to account for offset
        with_payload=True,
        query_filter={
            "must": [
                {"key": "category", "match": {"value": category}},
                {"key": "difficulty", "match": {"value": difficulty}}
            ]
        }
    )
    
    # Apply offset manually since Qdrant search doesn't have offset parameter
    if offset > 0 and len(results) > offset:
        results = results[offset:]
    else:
        results = results
    questions = [
    {
        "id": r.id,
        "score": r.score,
        "text": r.payload.get("text"),
        "category": r.payload.get("category"),
        "skill": r.payload.get("skill"),  # <-- Add this line
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

    # Step 4: Divide skill questions by difficulty with deduplication ensuring target count
    import numpy as np
    final_questions = []
    selected_embeddings = []
    SIMILARITY_THRESHOLD = 0.85  # Adjust as needed
    
    # Create a pool of all possible questions organized by (category, skill, difficulty)
    question_pools = {}
    
    # First pass: collect initial questions with over-fetching to account for deduplication
    for (category, skill), num_q in skill_questions.items():
        for difficulty, ratio in difficulty_ratios.items():
            num_diff_q = math.floor(num_q * ratio)
            # Distribute any remainder to Beginner first
            if difficulty == "Beginner":
                num_diff_q += num_q - sum(math.floor(num_q * r) for r in difficulty_ratios.values())
            if num_diff_q > 0:
                # Fetch more questions than needed to account for potential duplicates
                fetch_count = max(num_diff_q * 3, 50)  # Fetch 3x more or minimum 50
                results = search_questions_by_skill_category_difficulty(skill, category, difficulty, fetch_count)
                
                # Filter out questions with invalid options (like "Option 1", "Option 2", etc.)
                valid_results = []
                invalid_count = 0
                for q in results:
                    if is_valid_question(q):
                        valid_results.append(q)
                    else:
                        invalid_count += 1
                
                print(f"[allocate_and_retrieve_questions] Fetched {len(results)} questions for skill '{skill}', category '{category}', difficulty '{difficulty}' (needed: {num_diff_q})")
                if invalid_count > 0:
                    print(f"[allocate_and_retrieve_questions] Filtered out {invalid_count} questions with invalid options (e.g., 'Option 1', 'Option 2')")
                
                question_pools[(category, skill, difficulty)] = {
                    'questions': valid_results,
                    'needed': num_diff_q,
                    'selected': 0
                }
    
    # Second pass: select questions with deduplication until we reach target
    max_attempts = 50  # Prevent infinite loops
    attempt = 0
    questions_needed = total_questions
    
    while len(final_questions) < questions_needed and attempt < max_attempts:
        attempt += 1
        questions_added_this_round = 0
        
        # Try to add questions from each pool that still needs more
        for (category, skill, difficulty), pool_info in question_pools.items():
            if pool_info['selected'] < pool_info['needed'] and pool_info['questions']:
                # Get next question from this pool
                for i, q in enumerate(pool_info['questions']):
                    if i < pool_info['selected']:  # Skip already processed questions
                        continue
                    
                    q_text = q.get("text")
                    if not q_text:
                        pool_info['selected'] += 1
                        continue
                    
                    # Check if question has valid options (not "Option 1", "Option 2", etc.)
                    if not is_valid_question(q):
                        pool_info['selected'] += 1
                        continue
                    
                    q_emb = embedding_model.encode([q_text])[0]
                    is_similar = False
                    
                    # Check for similarity with already selected questions
                    for emb in selected_embeddings:
                        sim = np.dot(q_emb, emb) / (np.linalg.norm(q_emb) * np.linalg.norm(emb))
                        if sim >= SIMILARITY_THRESHOLD:
                            is_similar = True
                            break
                    
                    pool_info['selected'] += 1
                    
                    if not is_similar:
                        final_questions.append(q)
                        selected_embeddings.append(q_emb)
                        questions_added_this_round += 1
                        print(f"[allocate_and_retrieve_questions] Added question {len(final_questions)}/{total_questions} from {skill}-{difficulty}")
                        break  # Move to next pool
                    
                    # Stop if we've reached our target
                    if len(final_questions) >= total_questions:
                        break
                
                if len(final_questions) >= total_questions:
                    break
        
        # If no questions were added this round, try fetching more from pools that need them
        if questions_added_this_round == 0 and len(final_questions) < total_questions:
            print(f"[allocate_and_retrieve_questions] Attempt {attempt}: Need {total_questions - len(final_questions)} more questions, fetching additional...")
            
            for (category, skill, difficulty), pool_info in question_pools.items():
                if pool_info['selected'] < pool_info['needed']:
                    # Fetch more questions from Qdrant
                    additional_questions = search_questions_by_skill_category_difficulty(
                        skill, category, difficulty, 50, offset=len(pool_info['questions'])
                    )
                    if additional_questions:
                        # Filter valid questions before adding to pool
                        valid_additional = [q for q in additional_questions if is_valid_question(q)]
                        invalid_additional = len(additional_questions) - len(valid_additional)
                        
                        pool_info['questions'].extend(valid_additional)
                        print(f"[allocate_and_retrieve_questions] Fetched {len(valid_additional)} additional questions for {skill}-{difficulty}")
                        if invalid_additional > 0:
                            print(f"[allocate_and_retrieve_questions] Filtered out {invalid_additional} additional questions with invalid options")
                    
            # If still no new questions available, try fallback strategies
            if all(pool_info['selected'] >= len(pool_info['questions']) for pool_info in question_pools.values()):
                # Fallback 1: Lower similarity threshold
                if SIMILARITY_THRESHOLD > 0.7:
                    SIMILARITY_THRESHOLD -= 0.05
                    print(f"[allocate_and_retrieve_questions] Lowering similarity threshold to {SIMILARITY_THRESHOLD}")
                    # Reset pools for retry with lower threshold
                    for pool_info in question_pools.values():
                        pool_info['selected'] = 0
                    continue
                
                # Fallback 2: Get questions from any available category/difficulty
                print(f"[allocate_and_retrieve_questions] Attempting cross-category question retrieval...")
                categories_with_questions = []
                for (cat, skill, diff), pool_info in question_pools.items():
                    if pool_info['questions']:
                        categories_with_questions.append((cat, skill, diff))
                
                if categories_with_questions:
                    # Try to get more questions from categories that have them
                    for cat, skill, diff in categories_with_questions:
                        if len(final_questions) >= questions_needed:
                            break
                        additional = search_questions_by_skill_category_difficulty(
                            skill, cat, diff, 100, offset=len(question_pools[(cat, skill, diff)]['questions'])
                        )
                        if additional:
                            for q in additional:
                                if len(final_questions) >= questions_needed:
                                    break
                                q_text = q.get("text")
                                if not q_text:
                                    continue
                                # Check if question has valid options
                                if not is_valid_question(q):
                                    continue
                                q_emb = embedding_model.encode([q_text])[0]
                                is_similar = False
                                for emb in selected_embeddings:
                                    sim = np.dot(q_emb, emb) / (np.linalg.norm(q_emb) * np.linalg.norm(emb))
                                    if sim >= SIMILARITY_THRESHOLD:
                                        is_similar = True
                                        break
                                if not is_similar:
                                    final_questions.append(q)
                                    selected_embeddings.append(q_emb)
                    
                    if len(final_questions) < questions_needed:
                        print(f"[allocate_and_retrieve_questions] Warning: Could only find {len(final_questions)} unique questions out of {questions_needed} requested")
                break
    
    # Final check: If we still don't have enough questions, fill up with any available questions
    if len(final_questions) < questions_needed:
        print(f"[allocate_and_retrieve_questions] Final fallback: need {questions_needed - len(final_questions)} more questions")
        all_available_questions = []
        for pool_info in question_pools.values():
            all_available_questions.extend(pool_info['questions'])
        
        # Remove questions we've already added
        final_question_texts = [q.get("text", "") for q in final_questions]
        for q in all_available_questions:
            if len(final_questions) >= questions_needed:
                break
            q_text = q.get("text", "")
            if q_text and q_text not in final_question_texts and is_valid_question(q):
                final_questions.append(q)
                print(f"[allocate_and_retrieve_questions] Added fallback question {len(final_questions)}/{questions_needed}")
    
    # Ensure we don't exceed the requested number
    if len(final_questions) > questions_needed:
        final_questions = final_questions[:questions_needed]
    
    print(f"[allocate_and_retrieve_questions] Returning {len(final_questions)} total questions (after deduplication) in {attempt} attempts.")
    return final_questions

def test_question_allocation():
    """Test the enhanced question allocation with guaranteed 30 unique questions"""
    print("\n" + "="*60)
    print("TESTING ENHANCED QUESTION ALLOCATION (30 UNIQUE QUESTIONS)")
    print("="*60)
    
    # Test with skills that have enough questions in Qdrant
    selected_categories_skills = {
        "Programming Languages": ["Python", "Java", "C++"]
    }
    
    print(f"Selected categories and skills: {selected_categories_skills}")
    
    # Test with 30 questions (ensuring exactly 30 unique after deduplication)
    result = allocate_and_retrieve_questions(selected_categories_skills, total_questions=30)
    
    print(f"\nFinal Result: {len(result)} unique questions generated")
    print(f"Target was: 30 questions")
    
    if len(result) == 30:
        print("✅ SUCCESS: Exactly 30 unique questions generated after deduplication!")
    else:
        print(f"⚠️  WARNING: Got {len(result)} questions instead of 30")
    
    # Show breakdown by category and difficulty
    category_breakdown = {}
    difficulty_breakdown = {"Beginner": 0, "Intermediate": 0, "Advanced": 0}
    
    for q in result:
        cat = q.get("category", "Unknown")
        diff = q.get("difficulty", "Unknown")
        
        if cat not in category_breakdown:
            category_breakdown[cat] = 0
        category_breakdown[cat] += 1
        
        if diff in difficulty_breakdown:
            difficulty_breakdown[diff] += 1
    
    print(f"\nBreakdown by Category: {category_breakdown}")
    print(f"Breakdown by Difficulty: {difficulty_breakdown}")
    
    return result

if __name__ == "__main__":
    # Uncomment these lines if you need to setup Qdrant initially
    # create_collection()
    # sync_questions_from_mongo_to_qdrant()
    
    # Test the enhanced allocation
    test_question_allocation()