


import requests
import pymongo
import json

def generate_skills_with_prompt():
    prompt = '''
    List all possible skills a fresher should have to join a multinational company like Lenovo, which handles multiple verticals (IT, engineering, business, support, etc.).
    Group the skills by category. Categories should include (but are not limited to):
    - Programming Languages
    - Web Development
    - Mobile Development
    - Data Science & Analytics
    - Cloud Computing
    - Databases
    - Networking
    - Cybersecurity
    - Operating Systems
    - Hardware & Embedded
    - Testing
    - Version Control
    - Business Analysis
    - Communication
    - Customer Support
    - Soft Skills
    - Emerging Technologies
    - Other Useful Skills

    IMPORTANT:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    ``````````````````````````````````````````````````````````````````````````````````    - Do NOT include categories like Project Management or DevOps unless the skills are truly entry-level and relevant for freshers.
    - Ensure each skill appears in only one, most relevant category. Do NOT repeat skills across categories.
    - Group related or synonymous skills as a single entry, for example:
        - "SQL/MySQL" (not separate)
        - "Excel/Spreadsheets"
        - "Power BI/Tableau"
        - "HTML/CSS"
        - "Linux/Unix"
        - "Git/GitHub"
        - "JavaScript/TypeScript"
        - "REST/Web APIs"
        - "MS Office Suite" (for Word, PowerPoint, Excel)
    - Avoid listing advanced frameworks, cloud platforms, or tools unless they are truly entry-level or part of the job description.
    - Only output the JSON object, no explanation or markdown.
    - Example format:
    {
        "Programming Languages": ["Python", "Java", ...],
        "Web Development": ["HTML/CSS", ...],
        "Databases": ["SQL/MySQL", "MongoDB", ...],
        "Data Science & Analytics": ["Excel/Spreadsheets", "Power BI/Tableau", ...],
        ...
    }
    '''
    # Replace with your LLM API endpoint and payload
    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama2",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(ollama_url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        generated_text = result.get('response', '')
        skills_data = json.loads(generated_text)
        return skills_data
    except Exception as e:
        print(f"Error generating skills with prompt: {e}")
        return {}

def save_skills_to_mongodb(skills_data):
    if not skills_data:
        print("No skills data to save!")
        return False
    try:
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client['internship-program']
        collection = db['all_skills']
        collection.delete_many({})
        docs = [{"category": k, "skills": v} for k, v in skills_data.items()]
        collection.insert_many(docs)
        print("Skills saved to MongoDB under 'all_skills' (category-wise).")
        return True
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")
        return False

def main():
    print("[INFO] Generating all possible skills for MNC fresher using LLM prompt...")
    skills_data = generate_skills_with_prompt()
    if skills_data:
        # Post-process to remove duplicate skills across categories
        seen_skills = set()
        cleaned_skills_data = {}
        for category, skills in skills_data.items():
            unique_skills = []
            for skill in skills:
                skill_norm = skill.strip().lower()
                if skill_norm not in seen_skills:
                    unique_skills.append(skill)
                    seen_skills.add(skill_norm)
            if unique_skills:
                cleaned_skills_data[category] = unique_skills
        print("[INFO] Generated and cleaned skills:", cleaned_skills_data)
        save_skills_to_mongodb(cleaned_skills_data)
    else:
        print("[ERROR] Failed to generate skills.")

if __name__ == "__main__":
    main()