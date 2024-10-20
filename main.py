from fastapi.responses import HTMLResponse
from fastapi import (
    FastAPI,
    Request,
    Form,
    UploadFile,
    File,
)
from starlette.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
import shutil
from pdf import upload_to_gemini, generate_topics, generate_topic_notes, generate_quiz
from passlib.context import CryptContext
import logging
from db import hash_password, verify_password
from fastapi.templating import Jinja2Templates
from pdf import generate_notes
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
import html

load_dotenv()


# Set up FastAPI
app = FastAPI()
# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add session middleware (from starlette)
app.add_middleware(SessionMiddleware, secret_key="your_secret_key_here")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Mock database connection function
def get_db_connection():
    """Establish and return a connection to the database."""
    return psycopg2.connect(
        database=os.getenv("SUPABASE_DATABASE"),
        user=os.getenv("SUPABASE_USER"),
        password=os.getenv("SUPABASE_PASSWORD"),
        host=os.getenv("SUPABASE_HOST"),
    )


# Sign-up route
@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    """Render the signup page."""
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    """Handle user signup process."""
    conn = get_db_connection()
    cur = conn.cursor()
    hashed_password = hash_password(password)
    try:
        # Insert new user into the database
        cur.execute(
            "INSERT INTO authentication (email, username, password) VALUES (%s, %s, %s)",
            (email, username, hashed_password),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        # Handle case where email or username already exists
        conn.rollback()
        return HTMLResponse(status_code=400, content="Email or Username already exists")
    finally:
        cur.close()
        conn.close()

    return RedirectResponse(url="/login", status_code=302)


# Login route
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Render the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
):
    """Handle user login process."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Fetch user from database
        cur.execute(
            "SELECT * FROM authentication WHERE email = %s or username = %s",
            (login, login),
        )
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    # Verify user credentials
    if not user or not verify_password(password, user["password"]):
        return HTMLResponse(status_code=400, content="Invalid email or password")

    # Store user information in session
    request.session["email"] = user["email"]
    request.session["username"] = user["username"]

    return RedirectResponse(url="/", status_code=302)


# Configure logging
logging.basicConfig(level=logging.INFO)


@app.get("/logout")
def logout(request: Request):
    """Handle user logout process."""
    username = request.session.get("username")
    logging.info(f"Logging out user: {username}")

    # Clear the session
    request.session.clear()

    # Redirect to home page
    response = RedirectResponse(url="/")
    logging.info("Session cleared. Redirecting to home page.")
    return response


# Home route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    username = request.session.get("username")
    email = request.session.get("email")
    return templates.TemplateResponse(
        "index.html", {"request": request, "username": username, "email": email}
    )


@app.post("/upload_pdf/")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """Handle PDF upload and store file reference in session."""
    username = request.session.get("username")
    if not username:
        return JSONResponse(
            content={"error": "You need to be logged in to upload a file."},
            status_code=401,
        )

    # Validate file type
    if file.content_type != "application/pdf":
        return JSONResponse(
            content={"error": "Invalid file type. Please upload a PDF file."},
            status_code=400,
        )

    # Create a unique folder for the user
    user_folder = Path("uploads") / username
    user_folder.mkdir(parents=True, exist_ok=True)

    # Save the file locally in the user's folder
    file_path = user_folder / os.path.basename(str(file.filename))
    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Upload the file to Gemini and store its URI in the session
    uploaded_file = upload_to_gemini(file_path)

    # Store the file path relative to the uploads folder in the session
    request.session["uploaded_file_path"] = str(file_path.relative_to(Path("uploads")))

    # Generate topics after file upload
    topics = generate_topics(uploaded_file)

    return {"message": "File uploaded", "file_name": file_path.name, "topics": topics}


# Add this function to escape the markdown
def escape_markdown(text):
    return html.escape(text)


# Add the custom filter to Jinja2
templates.env.filters["escape_markdown"] = escape_markdown


@app.get("/quiz/{chapter}")
async def quiz_page(request: Request, chapter: str):
    """Render the quiz page for a specific chapter."""
    return templates.TemplateResponse(
        "quiz.html", {"request": request, "chapter": chapter}
    )


@app.get("/api/quiz/{chapter}")
async def get_quiz(request: Request, chapter: str):
    """Generate and return a quiz for the specified chapter."""
    relative_file_path = request.session.get("uploaded_file_path")
    if not relative_file_path:
        logging.error("No file found in session")
        return JSONResponse(
            content={"error": "No file found in session. Please upload a PDF."},
            status_code=400,
        )

    file_path = Path("uploads") / relative_file_path
    if not file_path.exists():
        logging.error(f"File not found: {file_path}")
        return JSONResponse(
            content={
                "error": "File not found in storage. Please upload the PDF again."
            },
            status_code=400,
        )

    try:
        file = upload_to_gemini(file_path)
        logging.info(f"Uploaded file to Gemini: {file}")
        quiz_questions = generate_quiz(file, chapter)
        logging.info(f"Generated quiz questions: {quiz_questions}")
        return JSONResponse(content={"questions": quiz_questions})
    except Exception as e:
        logging.error(f"Error generating quiz: {str(e)}")
        return JSONResponse(
            content={"error": f"Error generating quiz: {str(e)}"}, status_code=500
        )


@app.get("/topic/{chapter}/{topic}")
async def topic_page(request: Request, chapter: str, topic: str):
    """Render the topic page."""
    return templates.TemplateResponse(
        "topic.html", {"request": request, "chapter": chapter, "topic": topic}
    )


@app.get("/subtopic/{chapter}/{topic}/{subtopic}")
async def subtopic_page(request: Request, chapter: str, topic: str, subtopic: str):
    """Render the subtopic page."""
    return templates.TemplateResponse(
        "subtopic.html",
        {
            "request": request,
            "chapter": chapter,
            "topic": topic,
            "subtopic": subtopic,
        },
    )


@app.get("/api/notes/{chapter}/{topic}/{subtopic}")
async def get_notes(request: Request, chapter: str, topic: str, subtopic: str):
    """Generate notes for the subtopic and return JSON."""
    relative_file_path = request.session.get("uploaded_file_path")
    if not relative_file_path:
        return JSONResponse(
            content={"error": "No file found in session. Please upload a PDF."},
            status_code=400,
        )

    file_path = Path("uploads") / relative_file_path
    if not file_path.exists():
        return JSONResponse(
            content={
                "error": "File not found in storage. Please upload the PDF again."
            },
            status_code=400,
        )

    try:
        notes = generate_notes(chapter, topic, subtopic, file_path)
        if not notes.strip():
            notes = "No notes generated for this subtopic."
        return JSONResponse(content={"notes": notes})
    except Exception as e:
        logging.error(f"Error generating notes: {str(e)}")
        return JSONResponse(
            content={"error": f"Error generating notes: {str(e)}"}, status_code=500
        )


@app.get("/api/topic_notes/{chapter}/{topic}")
async def get_topic_notes(request: Request, chapter: str, topic: str):
    """Generate notes for the topic and return JSON."""
    relative_file_path = request.session.get("uploaded_file_path")
    if not relative_file_path:
        return JSONResponse(
            content={"error": "No file found in session. Please upload a PDF."},
            status_code=400,
        )

    file_path = Path("uploads") / relative_file_path
    if not file_path.exists():
        return JSONResponse(
            content={
                "error": "File not found in storage. Please upload the PDF again."
            },
            status_code=400,
        )

    try:
        file = upload_to_gemini(file_path)
        topic_notes = generate_topic_notes(file, chapter, topic)
        if not topic_notes.strip():
            topic_notes = "No notes generated for this topic."
        return JSONResponse(
            content={"chapter_overview": "", "topic_notes": topic_notes}
        )
    except Exception as e:
        logging.error(f"Error generating topic notes: {str(e)}")
        return JSONResponse(
            content={"error": f"Error generating topic notes: {str(e)}"},
            status_code=500,
        )
