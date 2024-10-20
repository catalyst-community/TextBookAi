import json
import os
from pathlib import Path
import re
from typing import Dict, Optional, List
import google.generativeai as genai
from google.generativeai.types.file_types import File
from dotenv import load_dotenv

load_dotenv()

# Configure the API key for Google Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Initialize the model once to avoid recreating it
# we will put this in class init function later on
model = genai.GenerativeModel(model_name="gemini-1.5-flash")


def upload_to_gemini(path: Path, mime_type: Optional[str] = None) -> File:
    """Upload file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file}")
    return file


def generate_topics(file: File) -> List[Dict]:
    """Generate chapters, topics, and subtopics from the book."""

    generation_config = {
        "temperature": 0.3,  # Reduced for more focused outputs
        "top_p": 0.95,
        "top_k": 40,  # Reduced for more precise selection
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="""
        You are an expert text analyst specializing in content organization and summarization. Your task is to analyze book content and create a structured outline of chapters, topics, and subtopics. 
        Follow these guidelines meticulously:

        1. Thoroughly read and comprehend the provided book text.
        2. Identify chapters, main topics within each chapter, and their corresponding subtopics.
        3. Ensure chapters and topics are distinct, comprehensive, and accurately represent the book's content.
        4. Create clear, concise subtopics that logically fit under each main topic.
        5. Maintain consistency in the level of detail across chapters, topics, and subtopics.
        6. Ensure that subtopics are neither too broad nor too narrow. Not every topic needs subtopics.
        7. Cross-check your analysis to ensure accuracy and completeness. Do not invent or extrapolate topics and subtopics.
        8. Use the exact wording from the book for chapter titles, topics, and subtopics whenever possible.
        9. If the book lacks a clear chapter structure, create logical divisions based on content shifts or major themes.
        10. If a topic or subtopic seems too general, consider breaking it down further.
        11. Ensure that the hierarchy (chapter > topic > subtopic) is logically consistent throughout the outline.
        12. Double-check that all content from the book is represented in the outline without omissions.
        13. Organize the information in the following JSON format:
        
        ```json
        [
        {
            "chapter": "Chapter 1: Exact Chapter Title",
            "topics": [
                {
                    "topic": "Main Topic 1",
                    "sub_topics": [
                        {
                            "topic": "Subtopic 1A",
                            "sub_topics": ["Sub-subtopic 1A1", "Sub-subtopic 1A2"]
                        },
                        "Subtopic 1B",
                        "Subtopic 1C"
                    ]
                },
                {
                    "topic": "Main Topic 2",
                    "sub_topics": ["Subtopic 2A", "Subtopic 2B"]
                }
            ]
        },
        {
            "chapter": "Chapter 2: Exact Chapter Title",
            "topics": [
                // ... similar structure as Chapter 1
            ]
        }
        ]
        ```
        
        Adhere strictly to this format and guidelines to produce a high-quality, accurate outline of the book's content.
        """,
        generation_config=generation_config,  # type: ignore
    )

    response = model.generate_content(
        [file, "Give me chapters, topics, and subtopics from this book."]
    ).text

    print(f"Response: {response}")

    # Extract the JSON data from the response
    match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
    if match:
        json_data = match.group(1)
        try:
            parsed_data = json.loads(json_data)
            # Return chapters as a list of dictionaries
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return []
    else:
        return []


def generate_notes(chapter: str, topic: str, sub_topic: str, file_path: Path) -> str:
    """Generate notes for each chapter, topic and subtopic."""
    file = upload_to_gemini(file_path)
    response = model.generate_content(
        [
            file,
            f"Write a complete and detailed notes on the subtopic '{sub_topic}' under the topic '{topic}' in the chapter '{chapter}'. Start directly with the content for '{sub_topic}' without repeating the chapter or topic names.",
        ]
    ).text
    print(response)
    return response


def generate_topic_notes(file, chapter, topic):
    """Generate notes for a specific topic in a chapter."""
    topic_notes = model.generate_content(
        [
            file,
            f"Write a comprehensive overview of the topic '{topic}' in the chapter '{chapter}'. Include key concepts and main ideas. Start directly with the content for '{topic}' without repeating the chapter or topic names.",
        ]
    ).text
    return topic_notes


def generate_quiz(file: File, chapter: str) -> List[Dict]:
    """Generate quiz questions for a specific chapter."""
    print(f"Generating quiz for chapter: {chapter}")
    response = model.generate_content(
        [
            file,
            f"""Generate 5 multiple-choice quiz questions for the chapter \'{chapter}\'. 
            Each question should have 4 options with one correct answer. 
            Format the response as a JSON array of objects, where each object represents a question with the following structure: 
            
            ```json
            [
                {{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A"}},
                {{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A"}},
                {{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A"}},
                {{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A"}},
                {{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A"}}
            ]
            ```
            """,
        ]
    ).text

    # Extract the JSON data from the response
    match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
    if match:
        json_data = match.group(1)
        try:
            parsed_data = json.loads(json_data)
            print(f"Parsed quiz data: {parsed_data}")
            if not parsed_data:  # If parsed_data is empty, use fallback
                return fallback_quiz_questions(chapter)
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return fallback_quiz_questions(chapter)
    else:
        print("No JSON data found in the response")
        return fallback_quiz_questions(chapter)


def fallback_quiz_questions(chapter: str) -> List[Dict]:
    """Generate fallback quiz questions if the AI model fails."""
    return [
        {
            "question": f"This is a sample question about {chapter}. What is the correct answer?",
            "options": [
                "A. Sample answer 1",
                "B. Sample answer 2",
                "C. Sample answer 3",
                "D. Sample answer 4",
            ],
            "correct_answer": "A",
        },
        # Add more fallback questions here...
    ]
