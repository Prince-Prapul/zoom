from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sqlite3
import aiohttp
import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY not found in the .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# 📦 Models
# -------------------------------

class TextInput(BaseModel):
    text: str
    num_questions: int = 5

class MCQQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

# -------------------------------
# 🤖 MCQ Generator
# -------------------------------

def generate_mcq(text: str, num_questions: int = 5) -> List[MCQQuestion]:
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
            if len(lines) == 5:
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
                    print(f"⚠️ Could not parse block:\n{block}")
            else:
                print(f"⚠️ Incorrect number of lines:\n{block}")

        return questions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {e}")

# -------------------------------
# Extract from .vtt
# -------------------------------

def extract_text_from_vtt(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    text_lines = []
    for line in lines:
        if re.match(r"^\d\d:\d\d:\d\d\.\d\d\d -->", line):
            continue
        elif line.strip().isdigit():
            continue
        elif line.strip() == "":
            continue
        else:
            text_lines.append(line.strip())

    return " ".join(text_lines)

# -------------------------------
# 🗃️ Store in SQLite
# -------------------------------

def store_mcqs_for_meeting(meeting_id: str, transcript_path: str, db_path: str = "mcq_questions.db"):
    transcript_text = extract_text_from_vtt(transcript_path)
    mcqs = generate_mcq(transcript_text)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS mcq_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id TEXT,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    ''')
    for mcq in mcqs:
        c.execute('''
            INSERT INTO mcq_questions (meeting_id, question, options, answer)
            VALUES (?, ?, ?, ?)
        ''', (meeting_id, mcq.question, '|'.join(mcq.options), mcq.correct_answer))

    conn.commit()
    conn.close()
    print(f"✅ Stored {len(mcqs)} MCQs for meeting ID: {meeting_id}")

# -------------------------------
# 🧾 Store from plain text
# -------------------------------

def store_mcqs_in_db(text: str, db_path: str = 'mcq_questions.db'):
    mcqs = generate_mcq(text)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS mcq_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id TEXT DEFAULT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    ''')
    for mcq in mcqs:
        c.execute('''
            INSERT INTO mcq_questions (question, options, answer)
            VALUES (?, ?, ?)
        ''', (mcq.question, '|'.join(mcq.options), mcq.correct_answer))

    conn.commit()
    conn.close()
    print(f"✅ Stored {len(mcqs)} MCQs (no meeting ID)")

# -------------------------------
# 📥 Upload .vtt transcript
# -------------------------------

@app.post("/upload_transcript/")
async def upload_transcript(meeting_id: str = Form(...), file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    try:
        store_mcqs_for_meeting(meeting_id, temp_path)
        return {"status": "Transcript processed and MCQs stored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    finally:
        os.remove(temp_path)

# -------------------------------
# 📤 Zoom Webhook
# -------------------------------

@app.post("/webhook")
async def zoom_webhook(request: Request):
    data = await request.json()

    print("🔔 Zoom Webhook Event Received")
    print(json.dumps(data, indent=2))

    if data.get("event") == "recording.transcript_completed":
        recording = data["payload"]["object"]
        recording_files = recording.get("recording_files", [])
        download_token = data.get("download_token")
        transcript_url = None
        meeting_id = recording.get("id")

        for file in recording_files:
            if file.get("file_type") == "TRANSCRIPT":
                transcript_url = file["download_url"]
                break

        if transcript_url:
            transcript_url += f"?access_token={download_token}"
            transcript_text = await download_transcript(transcript_url)
            if transcript_text:
                print("📝 Transcript downloaded.")
                store_mcqs_in_db(transcript_text)
            else:
                print("⚠️ Failed to download transcript.")
        else:
            print("⚠️ No transcript file found.")

    return JSONResponse(content={"status": "received"}, status_code=200)

async def download_transcript(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"❌ Failed to download transcript: {response.status}")
                    return ""
    except Exception as e:
        print(f"❌ Exception while downloading transcript: {e}")
        return ""

# -------------------------------
# 📘 Test Manual Text Input
# -------------------------------

@app.post("/generate_mcq", response_model=List[MCQQuestion])
async def generate_mcq_endpoint(text_input: TextInput):
    return generate_mcq(text_input.text, text_input.num_questions)


@app.get("/quiz/{meeting_id}", response_model=List[MCQQuestion])
async def get_quiz_for_meeting(meeting_id: str):
    try:
        conn = sqlite3.connect("mcq_questions.db")
        c = conn.cursor()
        c.execute('''
            SELECT question, options, answer
            FROM mcq_questions
            WHERE meeting_id = ?
        ''', (meeting_id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail="No quiz found for this meeting ID.")

        quiz = []
        for question, options_str, answer in rows:
            options = options_str.split('|')
            quiz.append(MCQQuestion(
                question=question,
                options=options,
                correct_answer=answer
            ))

        return quiz

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quiz: {e}")


# -------------------------------
# 🔥 Run locally
# -------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
