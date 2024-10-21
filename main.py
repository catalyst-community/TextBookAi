import traceback
from fastapi.responses import FileResponse, HTMLResponse
from fastapi import (
    FastAPI,
    Request,
    Form,
    UploadFile,
    File,
)
from sqlalchemy.orm import Session
from starlette.requests import Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import os
from starlette.middleware.sessions import SessionMiddleware
import shutil
from pdf import upload_to_gemini, generate_topics
from passlib.context import CryptContext
import logging
from db import hash_password, verify_password
from fastapi.templating import Jinja2Templates
from pdf import generate_notes
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from datetime import datetime

load_dotenv()


# Set up FastAPI
app = FastAPI()
# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static", StaticFiles(directory="uploads"), name="uploads")
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


def check_existing_pdf(pdf_path: str) -> bool:
    """Check if a PDF already exists in the database by its path."""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM pdfs WHERE pdf_path = %s;"
            cursor.execute(query, (pdf_path,))
            return cursor.fetchone() is not None
    except psycopg2.Error as e:
        print(f"Error checking PDF existence: {e}")
    finally:
        conn.close()
    return False


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

    # Ensure the upload folder exists
    upload_folder = Path("uploads")
    upload_folder.mkdir(exist_ok=True)

    # Save the file locally
    file_path = upload_folder / os.path.basename(str(file.filename))
    
    # Check if the PDF already exists
    if check_existing_pdf(str(file_path)):
        return JSONResponse(
            content={"error": "This PDF has already been uploaded. Please use the library section."},
            status_code=400,
        )

    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Upload the file to Gemini and store its URI in the session
    uploaded_file = upload_to_gemini(file_path)


    # Store the PDF path and username in the 'pdfs' table
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO pdfs (pdf_path, username) 
            VALUES (%s, %s) RETURNING pdfid
            """,
            (str(file_path), username),
        )
        pdf_row = cur.fetchone()
        if pdf_row:
            pdf_id = pdf_row[0]
        else:
            return JSONResponse(
                content={"error": "Failed to retrieve pdfid after insertion."},
                status_code=500,
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Database error: " + str(e)}, status_code=500
        )
    finally:
        cur.close()

    uploaded_file = upload_to_gemini(file_path)

    # Store only the file name in the session
    request.session["uploaded_file_name"] = file_path.name

    # Generate topics after file upload
    topics_data = generate_topics(uploaded_file)

    return {
        "message": "File uploaded and processed successfully.",
        "file_name": file_path.name,
        "topics": topics_data,
    }



@app.get("/notes/")
async def get_notes(request: Request, chapter: str, topic: str, subtopic: str):
    """Generate notes for the subtopic and render the notes.html template."""
    file_name = request.session.get("uploaded_file_name")
    if not file_name:
        return HTMLResponse(
            "No file found in session. Please upload a PDF.", status_code=400
        )

    # Retrieve the file from storage
    file_path = Path("uploads") / file_name
    if not file_path.exists():
        return HTMLResponse(
            "File not found in storage. Please upload the PDF again.", status_code=400
        )

    # Generate notes
    try:
        notes = generate_notes(chapter, topic, subtopic, file_path)
        if not notes.strip():
            notes = "No notes generated for this subtopic."
        # Update subtopic content in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE subtopics
            SET content = %s
            WHERE subtopicname = %s
            """,
            (notes, subtopic),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error generating notes: {str(e)}")
        notes = f"Error generating notes: {str(e)}"

    # Render the template with the generated notes
    return templates.TemplateResponse(
        "notes.html",
        {
            "request": request,
            "chapter": chapter,
            "topic": topic,
            "subtopic": subtopic,
            "notes": notes,
        },
    )


# Library Route
@app.get("/library", response_class=HTMLResponse)
async def library(request: Request):
    """Render the library page with options to search, view, and delete PDFs."""
    username = request.session.get("username")
    if not username:
        return JSONResponse(
            content={"error": "You need to be logged in to access the library."},
            status_code=401,
        )

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT pdfid, pdf_path FROM pdfs WHERE username = %s;""", (username,))
            pdfs = cur.fetchall()
            # Extract only the file names
            for pdf in pdfs:
                pdf["pdf_name"] = os.path.basename(pdf["pdf_path"])  # Get only the file name
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Database error: " + str(e)},
            status_code=500
        )
    finally:
        conn.close()

    return templates.TemplateResponse("library.html", {"request": request, "pdfs": pdfs})

@app.get("/uploads/{pdf_name}", response_class=HTMLResponse)
async def serve_pdf(pdf_name: str):
    """Serve PDF file directly from the uploads directory."""
    pdf_path = os.path.join("uploads", pdf_name)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found.")
    
    return FileResponse(pdf_path, media_type="application/pdf")

#View notes route
@app.get("/view_notes/{pdfid}/")
async def view_notes(request: Request, pdfid: int):
    """Retrieve notes for the given pdfid and render the notes.html template."""
    # Connect to the database
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch notes based on the pdfid
        cur.execute(
            """
            SELECT c.chaptername, t.topicname, s.subtopicname, s.content 
            FROM subtopics s
            JOIN topics t ON s.topicid = t.topicid
            JOIN chapters c ON t.chapterid = c.chapterid
            WHERE c.pdfid = %s
            """,
            (pdfid,)
        )
        notes_data = cur.fetchall()

        if not notes_data:
            return HTMLResponse(
                "No notes found for this PDF.", status_code=404
            )

        # Prepare notes content
        notes_content = ""
        for chaptername, topicname, subtopicname, content in notes_data:
            notes_content += f"## {chaptername}\n### {topicname}\n#### {subtopicname}\n{content}\n\n"

    except Exception as e:
        logging.error(f"Error retrieving notes: {str(e)}")
        return HTMLResponse(
            "An error occurred while retrieving notes.", status_code=500
        )
    finally:
        cur.close()
        conn.close()

    # Render the template with the retrieved notes
    return templates.TemplateResponse(
        "notes.html",
        {
            "request": request,
            "subtopic": "Notes",  # Change this as needed
            "notes": notes_content,
        },
    )



# Delete PDF Route
@app.post("/delete_pdf/{pdf_id}")
async def delete_pdf(pdf_id: int, request: Request):
    """Delete the PDF and its associated metadata."""
    username = request.session.get("username")
    if not username:
        return JSONResponse(
            content={"error": "You need to be logged in to delete a PDF."},
            status_code=401,
        )

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM subtopics WHERE topicid IN (SELECT topicid FROM topics WHERE chapterid IN (SELECT chapterid FROM chapters WHERE pdfid = %s));", (pdf_id,))
            cur.execute("DELETE FROM topics WHERE chapterid IN (SELECT chapterid FROM chapters WHERE pdfid = %s);", (pdf_id,))
            cur.execute("DELETE FROM chapters WHERE pdfid = %s;", (pdf_id,))
            cur.execute("DELETE FROM pdfs WHERE pdfid = %s AND username = %s;", (pdf_id, username))
            conn.commit()
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Failed to delete the PDF."}, status_code=500
        )
    finally:
        conn.close()

    return RedirectResponse(url="/library", status_code=302)

# Search PDF Route
@app.get("/library/search_pdf", response_class=HTMLResponse)
async def search_pdf(request: Request, query: str):
    """Search for PDFs by their name."""
    username = request.session.get("username")
    if not username:
        return JSONResponse(
            content={"error": "You need to be logged in to search PDFs."},
            status_code=401,
        )

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pdfid, pdf_path FROM pdfs
                WHERE username = %s AND pdf_path ILIKE %s;
            """, (username, f"%{query}%"))
            results = cur.fetchall()
            # Extract only the file names for each result
            for pdf in results:
                pdf["pdf_name"] = os.path.basename(pdf["pdf_path"])  # Get only the file name
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Database error: " + str(e)},
            status_code=500
        )
    finally:
        conn.close()

    return templates.TemplateResponse("library.html", {"request": request, "pdfs": results})

