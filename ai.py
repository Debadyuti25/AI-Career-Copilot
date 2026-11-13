import json
import os
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

def make_capital(text):
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]

def analyze_resume_with_ai(resume_text, user_goal):
    
    # 1. Check resume length
    if len(resume_text.strip()) < 30:
        return json.dumps({"error": "Invalid file or Resume text! Please upload a correct resume PDF/DOCX or Resume text."})

    # 2. Comprehensive Python-side Validation Check (Without relations list)
    INVALID_NAMES = [
        "debadyuti", "rohit", "priya", "alex", "jojo", "rahul", "amit", "sneha", 
        "puja", "pooja", "neha", "vikash", "vikram", "ananya", "riya", 
        "manish", "akash", "sunil", "deepak", "karan", "sonal", "kajol"
    ]
    
    RANDOM_KEYMASH = [
        "adgjv", "nrawp", "qweap", "adesvnbmkipo", "asdfgh", "lkjsghfjy", 
        "abcdhjs", "zxcvbnmpoi", "qwertyuiop", "lkjhgfdsamnbvcxz", "mnbvcxz",
        "poiuytrewq", "asdfghjkl", "zxcvbnm", "lkjhgfdsa", "qwerty"
    ]
    
    INVALID_NUMBERS = [
        "12345678910", "12357", "6438", "1234", "0000", "9999", 
        "1111", "12345", "54321", "987654321", "123456", "0"
    ]
    
    INVALID_FRUITS = [
        "apple", "mango", "banana", "orange", "grapes", "papaya", "guava", 
        "pineapple", "watermelon", "dragonfruit", "durian", "rambutan", 
        "mangosteen", "passionfruit", "starfruit", "kumquat", "lychee"
    ]
    
    INVALID_OBJECTS_AND_OTHERS = [
        "cycle", "car", "card", "bike", "pen", "pencil", "book", "table", 
        "chair", "laptop", "phone", "bottle", "dog", "cat", "lion", "tiger", 
        "red", "blue", "green", "yellow", "football", "cricket"
    ]

    cleaned_goal = user_goal.strip().lower()
    
    # Check if target role matches any blacklist or is too short
    if (cleaned_goal in INVALID_NAMES or 
        cleaned_goal in RANDOM_KEYMASH or 
        cleaned_goal in INVALID_NUMBERS or 
        cleaned_goal in INVALID_FRUITS or 
        cleaned_goal in INVALID_OBJECTS_AND_OTHERS or 
        len(cleaned_goal) < 2):
        
        return json.dumps({"error": "Invalid target role! Please enter a valid job position or career field."})

    # Strict Prompt for Gemini AI
    prompt = """
You are a strict Resume Validator and Career Coach.

Resume Text: """ + resume_text[:4500] + """
Target Role: """ + user_goal + """

STEP 1 - VALIDATION:
Check if the text is a real resume. A resume must contain at least 2 of: Name, Skills, Education, Experience, Projects, Email.
If the text is random words, a story, a bill, or just a goal like "I want to be developer" - it is NOT a resume.
If not a resume, return ONLY this JSON:
{"error": "Invalid file or Resume text! Please upload a correct resume PDF/DOCX or Resume text."}

CRITICAL NEGATIVE CONSTRAINT FOR TARGET Role:
Check if the target role """ + user_goal + """ is a human name (such as Rahul, Debadyuti, Rohit, Priya, etc.), random keyboard smashing, numbers, random objects, fruits, colors, or meaningless random letters.
If the target role is ANY of these invalid types, you are STRICTLY FORBIDDEN from generating an analysis report. You MUST return ONLY this exact JSON error object:
{"error": "Invalid target role! Please enter a valid job position or career field."}

IMPORTANT: If the target role is ANY real profession, job title, or career field (for example: Doctor, Software Engineer, Teacher, Data Scientist, Graphic Designer, etc.), you MUST accept it as valid.
Even if the resume background is different from the target role, treat it as a career transition goal, analyze the resume objectively, and provide the analysis.

STEP 2 - If it is a valid resume and a valid target role:
Analyze the resume thoroughly for the role """ + user_goal + """.
Return ONLY valid JSON with lowercase keys containing:
{
  "skills": ["List existing skills found in the resume"],
  "missing_skills": ["List missing skills required for the target role"],
  "roadmap": ["5 step personalized roadmap, each ending with a full stop."],
  "interview_questions": ["5 relevant technical interview questions, each ending with a question mark?"],
  "match_percentage": <integer between 0 to 100 based on actual resume match>,
  "feedback": "Detailed constructive AI feedback evaluating the resume for this role."
}
"""

    for model in MODELS_TO_TRY:
        try:
            print("Trying " + model + " for role: " + user_goal)
            response = client.models.generate_content(model=model, contents=prompt)
            text = response.text
            
            s = text.find("{")
            e = text.rfind("}") + 1
            if s != -1 and e != -1:
                json_str = text[s:e]
                json_str = re.sub(r',\s*}', '}', json_str)
                parsed = json.loads(json_str)
                
                if "error" in parsed:
                    return json.dumps(parsed)

                if "Roadmap" in parsed:
                    parsed["roadmap"] = parsed.pop("Roadmap")

                parsed["roadmap"] = [make_capital(x) for x in parsed.get("roadmap", [])]
                parsed["interview_questions"] = [make_capital(x) for x in parsed.get("interview_questions", [])]
                parsed["skills"] = [make_capital(x) for x in parsed.get("skills", [])]
                parsed["missing_skills"] = [make_capital(x) for x in parsed.get("missing_skills", [])]
                
                if "match_percentage" not in parsed or not isinstance(parsed["match_percentage"], int):
                    parsed["match_percentage"] = 50

                print("SUCCESS")
                return json.dumps(parsed)

        except Exception as e:
            print("Model failed: " + str(e))
            continue
    
    return json.dumps({
        "error": "AI API Failed. Please check your GEMINI_API_KEY in .env file."
    })