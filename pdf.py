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
        "temperature": 0.5,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    print("-------------------------------------------")
    print("file:", file)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="""You are an expert text analyst specializing in content organization and summarization. Your task is to analyze book content and create a structured outline of chapters, topics, and subtopics. 
                            Follow these guidelines:
                            1. Carefully read and comprehend the provided book text.
                            2. Identify chapters, then main topics within each chapter, and their corresponding subtopics.
                            3. Ensure chapters and topics are distinct, comprehensive, and accurately represent the book's content.
                            4. Create clear, concise subtopics that logically fit under each main topic.
                            5. Maintain consistency in the level of detail across chapters, topics, and subtopics.
                            6. Cross-check your analysis to ensure accuracy and completeness.
                            7. Organize the information in the following JSON format:
                            
                            ```json
                            [
                            {
                                "chapter": "Chapter 1: Chapter Title",
                                "topics": [
                                    {
                                        "topic": "Main Topic 1",
                                        "sub_topics": ["Subtopic 1A", "Subtopic 1B", "Subtopic 1C"]
                                    },
                                    {
                                        "topic": "Main Topic 2",
                                        "sub_topics": ["Subtopic 2A", "Subtopic 2B"]
                                    }
                                ]
                            },
                            {
                                "chapter": "Chapter 2: Chapter Title",
                                "topics": [
                                    // ... similar structure as Chapter 1
                                ]
                            }
                            ]
                            ```
                            
                            8. Ensure all chapter, topic, and subtopic names are descriptive and meaningful.
                            9. If a topic has complex structure, you may use nested subtopics as needed.
                            10. Aim for a balance between detail and brevity in your outline.
                            11. If you encounter any ambiguities or difficulties in categorization, explain your reasoning briefly after the JSON output.
                            Remember to thoroughly review your output for accuracy, consistency, and proper JSON formatting before submitting your response.
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
            f"Write a complete and detailed notes on the subtopic '{sub_topic}' under the topic '{topic}' in the chapter '{chapter}'.",
        ]
    ).text
    print(response)
    return response
