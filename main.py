from fastapi import FastAPI, File, UploadFile, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from pdf import generate_notes, upload_to_gemini, generate_topics
from starlette.middleware.sessions import SessionMiddleware
import shutil

app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# Set the template directory for Jinja2
templates = Jinja2Templates(directory="templates")


# Route for the home page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload_pdf/")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """Handle PDF upload and store file reference in session."""
    # Validate file type
    if file.content_type != "application/pdf":
        return {"error": "Invalid file type. Please upload a PDF file."}

    # Ensure the upload folder exists
    upload_folder = Path("uploads")
    upload_folder.mkdir(exist_ok=True)

    # Save the file locally (sanitize file name)
    file_path = upload_folder / os.path.basename(str(file.filename))
    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)  # Save the file content

    # Upload the file to Gemini and store its URI in the session
    uploaded_file = upload_to_gemini(file_path)

    # Store only the file name in the session
    request.session["uploaded_file_name"] = file_path.name

    # Generate topics after file upload
    topics = generate_topics(uploaded_file)

    return {"message": "File uploaded", "file_name": file_path.name, "topics": topics}


@app.get("/subtopic/")
async def get_subtopic_notes(topic: str, subtopic: str, request: Request):
    """Retrieve the file from storage and generate notes for the subtopic."""
    file_name = request.session.get("uploaded_file_name")
    if not file_name:
        return HTMLResponse(
            content="No file found in session. Please upload a PDF.", status_code=400
        )

    # Retrieve the file from storage
    file_path = Path("uploads") / file_name
    if not file_path.exists():
        return HTMLResponse(
            content="File not found in storage. Please upload the PDF again.",
            status_code=400,
        )

    # Generate notes
    response = generate_notes(topic, subtopic, file_path)

    # Return formatted HTML
    html_content = f"""
    <html>
    <head>
        <title>{subtopic} Notes</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" />
    </head>
    <body>
        <div class="container mt-5">
            <h1>Notes for {subtopic}</h1>
            <p><strong>Topic:</strong> {topic}</p>
            <p><strong>Subtopic:</strong> {subtopic}</p>
            <div class="notes">{response}</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
