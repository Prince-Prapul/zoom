from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import List
import re

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY not found in the .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

class TextInput(BaseModel):
    text: str
    num_questions: int = 3

class MCQQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

def generate_mcq(text: str, num_questions: int = 3) -> List[MCQQuestion]:
    prompt = f"""Generate {num_questions} multiple-choice questions from the text below.

TEXT:
{text}

FORMAT STRICTLY LIKE THIS:
Question (do not include numbering):
a) Option A
b) Option B
c) Option C
d) Option D (Correct)

Only include each question block once. Separate each question block with exactly one blank line."""

    try:
        response = model.generate_content(prompt)
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise HTTPException(status_code=400, detail=f"Prompt was blocked: {response.prompt_feedback.block_reason}")

        generated_text = response.text.strip()
        print("=== RAW GEMINI OUTPUT ===\n", generated_text)

        raw_blocks = re.split(r"\n\s*\n", generated_text)
        questions = []

        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split('\n')
            if len(lines) == 5:  # Exactly 5 lines: Question + 4 options
                question_text = lines[0].replace("Question:", "").strip()
                options = {}
                correct_answer = None

                for line in lines[1:]:
                    match = re.match(r"^([a-d])\)\s*(.*?)(?:\s*\(Correct\))?$", line)
                    if match:
                        label = match.group(1)
                        option_text = match.group(2).strip()
                        options[label] = option_text
                        if "(Correct)" in line:
                            correct_answer = option_text

                if len(options) == 4 and correct_answer:
                    questions.append(MCQQuestion(
                        question=question_text,
                        options=list(options.values()),
                        correct_answer=correct_answer
                    ))
                else:
                    print(f"Warning: Could not fully parse block (incorrect format):\n{block}")
            else:
                print(f"Warning: Incorrect number of lines in block (expected 5, got {len(lines)}):\n{block}")

        return questions

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {e}")

@app.post("/generate_mcq", response_model=List[MCQQuestion])
async def generate_mcq_endpoint(text_input: TextInput):
    return generate_mcq(text_input.text, text_input.num_questions)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
