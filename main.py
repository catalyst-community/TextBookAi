from fastapi import FastAPI, File, UploadFile, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from pdf import upload_to_gemini, generate_topics

app = FastAPI()

# Set the template directory for Jinja2
templates = Jinja2Templates(directory="templates")


# Route for the home page
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

        # Return the generated topics as JSON
        return {"topics": topics}

    finally:
        os.remove(file_location)


# Route to serve the subtopic page with the topic and subtopic passed as query params
@app.get("/subtopic", response_class=HTMLResponse)
async def subtopic(
    request: Request, topic: str = Query(...), subtopic: str = Query(...)
):
    # Render the subtopic.html page and pass the topic and subtopic to the template
    return templates.TemplateResponse(
        "subtopic.html", {"request": request, "topic": topic, "subtopic": subtopic}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
