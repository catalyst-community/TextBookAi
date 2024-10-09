from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import os
from pdf import upload_to_gemini, generate_topics
from passlib.context import CryptContext

# Set up FastAPI
app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Mock database function
def get_db_connection():
    return psycopg2.connect(
        database="myapp_db",
        user="myapp_user",
        password="password",
        host="localhost",
    )


# Hash the password
def hash_password(password: str):
    return pwd_context.hash(password)


# Verify password
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# Sign-up route
@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed_password = hash_password(password)
    try:
        cur.execute(
            "INSERT INTO authentication (emailID, username, password) VALUES (%s, %s, %s)",
            (email, username, hashed_password),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email or Username already exists")
    finally:
        cur.close()
        conn.close()
    return RedirectResponse(url="/login", status_code=302)


# Login route
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM authentication WHERE emailID = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return RedirectResponse(url="/", status_code=302)


# Home route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Route to upload PDF and generate topics
@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    temp_dir = Path("./temp_files")
    temp_dir.mkdir(exist_ok=True)

    if not file.filename:
        return {"error": "No file uploaded"}

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed"}

    file_location = temp_dir / file.filename
    with open(file_location, "wb") as f:
        f.write(await file.read())

    try:
        uploaded_file = upload_to_gemini(file_location, mime_type="application/pdf")
        topics = generate_topics(uploaded_file)
        return {"topics": topics}
    finally:
        os.remove(file_location)


# Subtopic route
@app.get("/subtopic", response_class=HTMLResponse)
async def subtopic(
    request: Request,
    topic: str = Query(...),
    subtopic: str = Query(...),
):
    return templates.TemplateResponse(
        "subtopic.html", {"request": request, "topic": topic, "subtopic": subtopic}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
