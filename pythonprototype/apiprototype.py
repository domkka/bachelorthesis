import os
from google import genai
from google.genai import types
import json
from pypdf import PdfReader
import re

def extract_sections_using_bookmarks(reader: PdfReader):
    """Splits the PDF into sections using its bookmarks (if available)."""
    sections = {}
    bookmarks = []

    for item in reader.outline:
        if "/Title" in item:
            title = item["/Title"]
            bookmarks.append(title)

    if not bookmarks:
        return {"Full Text": "\n".join(page.extract_text() for page in reader.pages if page.extract_text())}

    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() + "\n"

    all_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', all_text)
    # Extract text for each section
    for i in range(len(bookmarks)):
        title = bookmarks[i]
        next_title = bookmarks[i + 1] if i + 1 < len(bookmarks) else None

        section_start = all_text.split(title, 1)[1]
        if next_title and next_title in section_start:
            section_text = section_start.split(next_title, 1)[0]
        else:
            section_text = section_start

        sections[title] = section_text.strip()

    return sections


def extract_json_from_response(text):
    lines = text.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() =="```":
        lines = lines[:-1]

    json_content = "\n".join(lines)
    return json_content

def generate(pdf_text, checklist):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemma-3-27b-it"

    prompt = f"""
            Evaluate the following document with respect to the checklist criteria below:

            Document:
            \"\"\"{pdf_text}\"\"\"


            Checklist:
            {checklist}


            For each checklist item, provide:
            - `criterion`: the name of the checklist item
            - `status`: one of "Met", "Not Met"
            - `justification`: a short explanation of where or why the criterion is (not) met (e.g., section title, paragraph context, or quote)


            Output format:
            Return only valid JSON, structured like this:
            [
                {{
                  "category": "Open Methodology & Documentation",
                  "results": [
                    {{
                      "criterion": "...",
                      "status": "Met" | "Not Met",
                      "justification": "..."
                    }}
                  ]
                }},
                ...
            ]
            Do not include any explanation or commentary outside the JSON.
        """

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="text/plain",
    )
    total_tokens = client.models.count_tokens(
        model=model,contents=prompt
    )
    print(f"total tokens: {total_tokens}")
    print("generating response")
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config
    )

    return response.text

if __name__ == "__main__":
    file_name = "3706468.3706541.pdf"
    file_id = os.path.splitext(os.path.basename(file_name))[0]

    reader = PdfReader(f"lakproceedings/{file_name}")

    # Load checklist
    with open("checklist.json", "r") as file:
        reproducibility_checklist = json.load(file)


    #Choose sections to not exceed Token Count (15000)
    sections = extract_sections_using_bookmarks(reader)
    section_names = list(sections.keys())
    print("Available sections:")
    for i, name in enumerate(section_names, 0):
        print(f"{i}: {name}")

    selected_input = input("Enter the numbers to evaluate (comma-separated): ")
    selected_indices = [int(i.strip()) for i in selected_input.split(",") if i.strip().isdigit()]

    fused_texts = []
    for i in selected_indices:
        name = section_names[i]
        section_text = sections[name]
        if section_text is None:
            print(f"Section '{name}' not found.")
            continue
        if not section_text:
            print(f"Section '{name}' is empty.")
            continue
        fused_texts.append(section_text)

    if fused_texts:
        combined_text = "\n\n".join(fused_texts)

    response = generate(combined_text, reproducibility_checklist)

    responsejson = extract_json_from_response(response)
    if responsejson:
        try:
            parsed = json.loads(responsejson)
            wrapped_data = {
                "id": file_id,
                "evaluation": parsed
            }

            output_path = f"generatedjson/{file_id}_evaluation.json"
            with open(output_path, "w") as f:
                json.dump(wrapped_data, f, indent=2)

            print(f"saved JSON to {output_path}")
        except json.JSONDecodeError:
            print("failed to parse JSON string")
    else:
        print("Failed to generate a valid JSON response.")
        print(f"Raw Response: {response}")