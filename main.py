from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from pdf import upload_to_gemini, generate_topics

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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

        # Ensure topics are returned as JSON
        return {"topics": topics}

    finally:
        os.remove(file_location)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
