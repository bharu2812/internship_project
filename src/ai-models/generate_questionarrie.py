import requests
import json
import pymongo

class OllamaQuestionGenerator:
    def __init__(self, ollama_host="http://localhost:11434", model_name="llama2"):
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.ollama_url = f"{ollama_host}/api/generate"

        # Connect to MongoDB
        self.client = pymongo.MongoClient('mongodb://localhost:27017/')
        self.db = self.client['internship-program']
        self.collection = self.db['generated_questions']
        
        # Create indexes
        try:
            self.collection.create_index("question_id", unique=True)
            self.collection.create_index("skill")
            self.collection.create_index("difficulty")
        except:
            pass

    def generate_mcq(self, domain, difficulty, topic=None, max_retries=3):
        """Generate a single MCQ for a given difficulty using Ollama, retrying if JSON parsing fails"""
        topic_text = f" specifically about {topic}" if topic else ""
        prompt = f"""
        Generate a multiple choice question (MCQ) for the {domain} domain at {difficulty} level{topic_text}.

        IMPORTANT: Your response MUST be valid JSON. Do NOT include any explanation, markdown, or extra text. Only output the JSON object as shown below:
        {{
            "question": "The MCQ question",
            "options": ["option1", "option2", "option3", "option4"],
            "answer": "Correct option",
            "explanation": "Short explanation",
            "tags": ["mcq", "{difficulty.lower()}", "{domain}"]
        }}

        Domain: {domain}
        Difficulty: {difficulty}
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(self.ollama_url, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                generated_text = result.get('response', '')
                mcq_data = json.loads(generated_text)
                mcq_data.update({
                    "domain": domain,
                    "difficulty": difficulty,
                    "question_id": None
                })
                return mcq_data
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to Ollama: {e}")
                return None
            except json.JSONDecodeError as e:
                print(f"[Attempt {attempt}] Error parsing JSON response: {e}")
                if attempt < max_retries:
                    print("Retrying...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    print("Max retries reached. Skipping this MCQ.")
                    return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None

    def save_to_mongodb(self, questions):
        """Save generated MCQs to MongoDB, keeping only required fields"""
        def filter_mcq_fields(q):
            allowed = {"question", "options", "answer", "explanation", "tags", "domain", "difficulty", "question_id"}
            return {k: v for k, v in q.items() if k in allowed}
        try:
            if questions:
                filtered = [filter_mcq_fields(q) for q in questions]
                result = self.collection.insert_many(filtered, ordered=False)
                return True
            else:
                print("No questions to save!")
                return False
        except pymongo.errors.BulkWriteError as e:
            print(f"Some questions already exist. Inserted: {e.details['nInserted']}")
            return True
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
            return False

    def get_database_stats(self):
        """Get statistics about generated questions"""
        total = self.collection.count_documents({})
        
        domains = list(self.collection.distinct("domain"))
        difficulties = list(self.collection.distinct("difficulty"))
        
        pipeline = [
            {
                "$group": {
                    "_id": {"domain": "$domain", "difficulty": "$difficulty"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        breakdown = list(self.collection.aggregate(pipeline))
        
        return {
            "total_questions": total,
            "domains": domains,
            "difficulties": difficulties,
            "breakdown": breakdown
        }

def main():
    # Connect to MongoDB and load all skills
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['internship-program']
    skills_collection = db['all_skills']
    skills_docs = list(skills_collection.find({}))

    generator = OllamaQuestionGenerator(
        ollama_host="http://localhost:11434",
        model_name="llama2"
    )

    print("[INFO] Starting MCQ generation for all skills and categories from all_skills collection...")
    print(f"[INFO] Using model: {generator.model_name}")

    import time
    start_time = time.time()

    last_entry = generator.collection.find_one(sort=[("question_id", -1)])
    mcq_id = last_entry['question_id'] + 1 if last_entry else 1

    total_mcqs = 0
    difficulties = ["Beginner", "Intermediate", "Advanced"]
    min_questions = 10

    for doc in skills_docs:
        category = doc.get('category', 'Unknown')
        skills = doc.get('skills', [])
        for skill in skills:
            print(f"\nProcessing skill: {skill} (Category: {category})")
            for difficulty in difficulties:
                existing_questions = list(generator.collection.find({
                    "domain": skill,
                    "difficulty": difficulty
                }))
                existing_count = len(existing_questions)

                if existing_count >= min_questions:
                    print(f"  Skipping {difficulty} for {skill}, already has {existing_count} questions.")
                    # Update missing category if needed
                    for q in existing_questions:
                        if 'category' not in q or not q['category']:
                            result = generator.collection.update_one(
                                {"_id": q["_id"]},
                                {"$set": {"category": category}}
                            )
                            if result.modified_count > 0:
                                print(f"    Updated existing question_id {q['question_id']} with category '{category}'")
                    continue

                needed = min_questions - existing_count
                print(f"  Generating {needed} more {difficulty} questions for {skill}")

                generated_count = 0
                attempts = 0
                while generated_count < needed and attempts < needed * 3:
                    print(f"    Generating {difficulty} MCQ {mcq_id} for skill: {skill}")
                    mcq = generator.generate_mcq(skill, difficulty)
                    if mcq:
                        mcq['question_id'] = mcq_id
                        mcq['category'] = category
                        mcq['skill'] = skill
                        saved = generator.save_to_mongodb([mcq])
                        if saved:
                            print(f"      Saved MCQ {mcq_id} to MongoDB.")
                            total_mcqs += 1
                            generated_count += 1
                        else:
                            print(f"      Failed to save MCQ {mcq_id}. It might already exist.")
                        mcq_id += 1
                    else:
                        print(f"      Failed to generate MCQ {mcq_id}.")
                    attempts += 1

                if generated_count < needed:
                    print(f"    Could only generate {generated_count}/{needed} questions for {skill} at {difficulty}.")

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\n[INFO] Total new MCQs saved: {total_mcqs}")
    print(f"[INFO] Time taken: {elapsed:.2f} seconds")
    print("[INFO] Updated database stats:", generator.get_database_stats())

if __name__ == "__main__":
    print("[INFO] Running generate_questionarrie.py")
    main()
