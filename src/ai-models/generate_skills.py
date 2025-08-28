import requests
import json
import pymongo
 
class OllamaSkillGenerator:
    def __init__(self, ollama_host="http://localhost:11434", model_name="llama2"):
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.ollama_url = f"{ollama_host}/api/generate"
        self.client = pymongo.MongoClient('mongodb://localhost:27017/')
        self.db = self.client['internship_project']
        self.collection = self.db['skills_list']
 
    def generate_skills(self, domain="CSE/IT", max_retries=3):
        prompt = f'''
        List all possible skills a student studying in the {domain} domain could have, grouped by category.
        Categories should include (but are not limited to): Programming Languages, Frameworks, Tools, Databases, Cloud, Soft Skills, Operating Systems, Concepts, and Emerging Technologies.
        Return the result as a valid JSON object with each category as a key and a list of skills as values. Example format:
        {{
            "Programming Languages": ["Python", "Java", ...],
            "Frameworks": ["Django", "React", ...],
            ...
        }}
        Only output the JSON object, no explanation or markdown.
        '''
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
                skills_data = json.loads(generated_text)
                return skills_data
            except Exception as e:
                print(f"[Attempt {attempt}] Error: {e}")
                if attempt < max_retries:
                    import time
                    time.sleep(2)
                    continue
                else:
                    return None
 
    def save_to_mongodb(self, skills_data):
        if not skills_data:
            print("No skills data to save!")
            return False
        try:
            # Remove previous data to avoid duplicates
            self.collection.delete_many({})
            docs = [{"category": k, "skills": v} for k, v in skills_data.items()]
            self.collection.insert_many(docs)
            print("Skills saved to MongoDB.")
            return True
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
            return False
 
def main():
    generator = OllamaSkillGenerator()
    print("[INFO] Generating CSE/IT skills using Ollama...")
    skills = generator.generate_skills()
    if skills:
        print("[INFO] Generated skills:", skills)
        generator.save_to_mongodb(skills)
    else:
        print("[ERROR] Failed to generate skills.")
 
if __name__ == "__main__":
    main()