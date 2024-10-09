import json
import os
from pathlib import Path
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
import google.generativeai as genai
from google.generativeai.types.file_types import File
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# Configure the API key for Google Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


@dataclass
class Topic:
    topic: str
    sub_topics: List[str]


@dataclass
class TopicOutput:
    topics: List[Topic]


# Initialize the model once to avoid recreating it
# we will put this in class init function later on
model = genai.GenerativeModel(model_name="gemini-1.5-flash")


def upload_to_gemini(path: Path, mime_type: Optional[str] = None) -> File:
    """Upload file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file}")
    return file


def generate_topics(file: File) -> List[Dict]:
    """Generate topics and subtopics from the book."""

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
        system_instruction="""Here's an enhanced version of the system prompt:
                            You are an expert text analyst specializing in content organization and summarization. Your task is to analyze book content and create a structured outline of topics and subtopics. 
                            Follow these guidelines:
                            1. Carefully read and comprehend the provided book text.
                            2. Identify main topics and their corresponding subtopics.
                            3. Ensure topics are distinct, comprehensive, and accurately represent the book's content.
                            4. Create clear, concise subtopics that logically fit under each main topic.
                            5. Maintain consistency in the level of detail across topics and subtopics.
                            6. Cross-check your analysis to ensure accuracy and completeness.
                            7. Organize the information in the following JSON format:
                            
                            ```json
                            [
                            {
                                "topic": "Main Topic 1",
                                "sub_topics": ["Subtopic 1A", "Subtopic 1B", "Subtopic 1C"]
                            },
                            {
                                "topic": "Main Topic 2",
                                "sub_topics": ["Subtopic 2A", "Subtopic 2B"]
                            }
                            ]
                            ```
                            
                            8. Ensure all topic and subtopic names are descriptive and meaningful.
                            9. If the book has a complex structure, consider using nested subtopics:
                            
                            ```json
                            [
                            {
                                "topic": "Main Topic 1",
                                "sub_topics": [
                                {
                                    "name": "Subtopic 1A",
                                    "sub_sub_topics": ["Sub-subtopic 1A.1", "Sub-subtopic 1A.2"]
                                },
                                "Subtopic 1B"
                                ]
                            }
                            ]
                            ```

                            10. If you encounter any ambiguities or difficulties in categorization, explain your reasoning briefly after the JSON output.
                            11. Aim for a balance between detail and brevity in your outline.
                            12. If the book is particularly long or complex, consider adding a "chapter" or "section" level to your JSON structure.
                            Remember to thoroughly review your output for accuracy, consistency, and proper JSON formatting before submitting your response.
                           """,
        generation_config=generation_config,  # type: ignore
    )

    response = model.generate_content(
        [file, "Give me topics and subtopics from this book."]
    ).text

    print(f"Response: {response}")

    # Extract the JSON data from the response
    match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
    if match:
        json_data = match.group(1)
        try:
            parsed_data = json.loads(json_data)
            # Return topics as a list of dictionaries
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return []
    else:
        return []


def generate_notes(topics: str, sub_topic: str, file_path: Path) -> str:
    """Generate notes for each topic and subtopic."""
    file = upload_to_gemini(file_path)
    response = model.generate_content(
        [
            file,
            f"Write short notes on the subtopic '{sub_topic}' under the topic '{topics}'.",
        ]
    ).text
    print(response)
    return response
