import os
from google import genai
from google.genai import types
import json
from pypdf import PdfReader
import re

def extract_sections_using_bookmarks(reader: PdfReader):
    """Splits the PDF into sections using bookmark page ranges."""
    sections = {}
    bookmarks = []

    for item in reader.outline:
        if isinstance(item, list):
            continue
        title = item.title
        try:
            page_number = reader.get_destination_page_number(item)
            bookmarks.append((title, page_number))
        except Exception:
            pass

    bookmarks.sort(key=lambda x: x[1])

    if not bookmarks:
        sections["Full Text"] = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        return sections

    # Extract text for each bookmark section
    for i, (title, start_page) in enumerate(bookmarks):
        end_page = (
            bookmarks[i + 1][1] if i + 1 < len(bookmarks) else len(reader.pages)
        )

        section_text = []
        for page_num in range(start_page, end_page):
            page_text = reader.pages[page_num].extract_text() or ""
            section_text.append(page_text)

        sections[title] = "\n".join(section_text).strip()

    return sections

def extract_json_from_response(text):
    # Regex to match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*(\[\s*[\s\S]*?\s*\])\s*```"

    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        raise ValueError("No JSON block found inside triple backticks.")

    json_str = match.group(1)
    return json_str

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
            
            !!!Do not include any explanation or commentary before or after the JSON!!!
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
    file_name = "thesis.pdf"
    file_id = os.path.splitext(os.path.basename(file_name))[0]
    reader = PdfReader(file_name)

    with open("checklist.json", "r") as file:
        reproducibility_checklist = json.load(file)

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
        if not section_text:
            print(f"Section '{name}' is empty.")
            continue
        fused_texts.append(section_text)

    if fused_texts:
        combined_text = "\n\n".join(fused_texts)

    response = generate(combined_text, reproducibility_checklist)
    print(response)

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