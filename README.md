
# QuizBot(Backend) for Zoom - Automatic Quiz Generation from Meeting Transcripts

HOME PAGE
<img width="1779" alt="image" src="https://github.com/user-attachments/assets/58097f47-7a82-4837-9dfc-ded2d6d7b1f6" />

QUIZ LAYOUT
<img width="1489" alt="image" src="https://github.com/user-attachments/assets/3f799b90-963d-437b-bf95-1f1893ee9e67" />


FEEDBACK LAYOUT 
<img width="1575" alt="image" src="https://github.com/user-attachments/assets/0011fec5-7a6b-49b5-a7b5-3464934be167" />

TECHNICAL WORKFLOW

![image](https://github.com/user-attachments/assets/683c070a-de28-4d3f-b043-3839acd1c447)


## Overview

QuizBot for Zoom is a FastAPI-based backend application designed to automatically generate multiple-choice quizzes from Zoom meeting transcripts using the power of the Google Gemini AI. This project aims to help students and professionals actively review meeting content and test their understanding in an interactive way.



## Tech Stack

* **Backend Framework:** FastAPI
* **AI Model:** Google Gemini API
* **Dependency Management:** pip with `requirements.txt`
* **Environment Variables:** `python-dotenv`
* **HTTP Client (for testing):** `requests`

## Prerequisites

* **Python 3.11** installed on your system.
* **pip3** (Python package installer).
* A Google Gemini API key. You can obtain one from [Google AI Studio](https://makersuite.google.com/).

## Setup

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone https://github.com/Prince-Prapul/zoom.git
    cd your_project_directory
    ```

2.  **Create a `.env` file:**
    In the root directory of the project, create a file named `.env` and add your Google Gemini API key:
    ```
    GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY
    ```
    Replace `YOUR_ACTUAL_GEMINI_API_KEY` with your obtained API key.

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the FastAPI Server

1.  Navigate to the project's root directory in your terminal.
2.  Run the FastAPI application using Uvicorn:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    * `main`: The name of your Python file containing the FastAPI application (e.g., `main.py`).
    * `app`: The name of your FastAPI application instance (e.g., `app = FastAPI()`).
    * `--reload`: Enables automatic reloading of the server upon code changes (useful for development).
    * `--host 0.0.0.0`: Makes the server accessible from any network interface.
    * `--port 8000`: Specifies the port the server will listen on.

## Using the API

You can send a POST request to the `/generate_mcq` endpoint to generate quizzes. The request body should be a JSON object with the following structure:

```json
{
    "text": "Your Zoom meeting transcript or any text you want to generate a quiz from.",
    "num_questions": 3 // Optional: The number of multiple-choice questions to generate (default is 3).
}
