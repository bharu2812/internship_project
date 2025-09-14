PLACEHOLDER_ANSWERS = {"corret", "option", "correct option", "corret option", "correct", "correct answer", "answer"}

def get_correct_answer(question, options):
	prompt = (
		f"Question: {question}\n"
		f"Options: {options}\n"
		f"Which one of the above options is the correct answer?\n"
		f"Return only the exact text of the correct option from the list above, nothing else."
	)
	payload = {
		"model": OLLAMA_MODEL,
		"prompt": prompt,
		"stream": False
	}
	try:
		response = requests.post(OLLAMA_URL, json=payload, timeout=60)
		response.raise_for_status()
		result = response.json()
		text = result.get("response", "").strip()
		# Try to match exactly one of the options
		for opt in options:
			if opt.strip().lower() == text.strip().lower():
				return opt
		# Fallback: try substring match
		for opt in options:
			if text.strip().lower() in opt.strip().lower() or opt.strip().lower() in text.strip().lower():
				return opt
		print(f"[WARN] LLM answer not matched exactly: '{text}' for options {options}")
		return text
	except Exception as e:
		print(f"[ERROR] Ollama call failed: {e}")
		return None
import requests
from pymongo import MongoClient

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama2"

def get_db():
	client = MongoClient("mongodb://localhost:27017/")
	db = client["internship-program"]
	return db

def generate_distractors(question, existing_options, needed):
	prompt = (
		f"Question: {question}\n"
		f"Existing options: {existing_options}\n"
		f"Generate {needed} additional plausible and relevant MCQ options (distractors) for this question, different from the existing ones. "
		f"Return only a valid Python list of strings, nothing else, no explanation, no extra text, no markdown. Strictly output a single Python list. Example: ['Option 1', 'Option 2']"
	)
	payload = {
		"model": OLLAMA_MODEL,
		"prompt": prompt,
		"stream": False
	}
	try:
		response = requests.post(OLLAMA_URL, json=payload, timeout=60)
		response.raise_for_status()
		result = response.json()
		import ast, re
		text = result.get("response", "")
		print(f"[DEBUG] Ollama raw response: {text}")
		# Try to extract a list from the response, even if extra text is present
		match = re.search(r'(\[.*?\])', text, re.DOTALL)
		if match:
			list_str = match.group(1)
			# Sanitize: replace problematic single quotes inside items
			# Replace unescaped single quotes inside words with double quotes
			list_str = re.sub(r"([a-zA-Z])'([a-zA-Z])", r"\\1’\\2", list_str)  # Use unicode right single quote for inner apostrophes
			try:
				distractors = ast.literal_eval(list_str)
				if isinstance(distractors, list):
					return [str(opt) for opt in distractors]
			except Exception as e:
				print(f"[ERROR] Failed to parse list from Ollama response: {e}")
		return []
	except Exception as e:
		print(f"[ERROR] Ollama call failed: {e}")
		return []

def main():
	db = get_db()
	collection = db["generated_questions"]
	count = 0
	for doc in collection.find({"options": {"$exists": True, "$type": "array"}}):
		options = doc["options"]
		updated = False
		# Fix options if less than 4
		if len(options) < 4:
			needed = 4 - len(options)
			print(f"[INFO] QID {doc.get('_id')}: Generating {needed} options for: {doc.get('question')}")
			distractors = generate_distractors(doc.get("question", ""), options, needed)
			if distractors:
				new_options = options + distractors[:needed]
				collection.update_one({"_id": doc["_id"]}, {"$set": {"options": new_options}})
				print(f"[SUCCESS] Updated options: {new_options}")
				options = new_options
				updated = True
			else:
				print(f"[FAIL] Could not generate distractors for QID {doc.get('_id')}")
		# Fix placeholder answers
		ans = str(doc.get("answer", "")).strip().lower()
		if ans in PLACEHOLDER_ANSWERS:
			print(f"[INFO] QID {doc.get('_id')}: Fixing placeholder answer for: {doc.get('question')}")
			correct = get_correct_answer(doc.get("question", ""), options)
			if correct:
				collection.update_one({"_id": doc["_id"]}, {"$set": {"answer": correct}})
				print(f"[SUCCESS] Updated answer: {correct}")
				ans = correct
				updated = True
			else:
				print(f"[FAIL] Could not get correct answer for QID {doc.get('_id')}")
		# Ensure answer is one of the options
		if ans and ans not in [str(opt).strip() for opt in options]:
			print(f"[WARN] QID {doc.get('_id')}: Answer not in options. Attempting to fix.")
			correct = get_correct_answer(doc.get("question", ""), options)
			if correct and correct in options:
				collection.update_one({"_id": doc["_id"]}, {"$set": {"answer": correct}})
				print(f"[SUCCESS] Updated answer to match options: {correct}")
				updated = True
			else:
				print(f"[FAIL] Could not fix answer for QID {doc.get('_id')}")
		if updated:
			count += 1
	print(f"Done. Updated {count} questions.")

if __name__ == "__main__":
	main()
