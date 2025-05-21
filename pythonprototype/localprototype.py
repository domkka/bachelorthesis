import os.path
import ollama
import json
from pypdf import PdfReader
import re

client = ollama.Client()
model = "gemma3:12b"

def extract_sections_using_bookmarks(reader: PdfReader):
    """Splits the PDF into sections using its bookmarks (if available)."""
    sections = {}
    bookmarks = []

    for item in reader.outline:
        if isinstance(item, list):  # Handle nested bookmarks
            continue
        if "/Title" in item:
            title = item["/Title"]
            bookmarks.append(title)

    if not bookmarks:
        return {"Full Text": "\n".join(page.extract_text() for page in reader.pages if page.extract_text())}

    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() + "\n"
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
    json_objects = []

    # Match code blocks with ```json\n...\n```
    code_blocks = re.findall(r'```(?:json)?\n([\s\S]+?)\n```', text)
    for block in code_blocks:
        try:
            json_objects.append(json.loads(block.strip()))
        except json.JSONDecodeError:
            pass

    # Match all possible JSON-like blocks: arrays or objects
    possible_blocks = re.findall(r'(\{[\s\S]*?\}|\[[\s\S]*?\])', text)
    for block in possible_blocks:
        try:
            json_objects.append(json.loads(block.strip()))
        except json.JSONDecodeError:
            pass

    if not json_objects:
        raise ValueError("No valid JSON objects found in the response")

    return json_objects[0]


def evaluate_section(document_section, checklist):
    checklist_text =""
    for section in checklist:
        category = section['category']
        criteria = "\n".join([
            f"- {item['name']}: {item['description']}"
            for item in section['criteria']
        ])
        checklist_text += f"\nCategory: {category}\n{criteria}\n"

    prompt = f"""
        Evaluate the following sections with respect to the checklist criteria below:
        
        Document:
        \"\"\"{document_section}\"\"\"
        
        
        Checklist:
        {checklist_text}
        
        
        For each checklist item, provide:
        - `criterion`: the name of the checklist item
        - `status`: one of "Met", "Partially Met", "Not Met", "Not Applicable"
        - `justification`: a short explanation of where or why the criterion is (not) met (e.g., section title, paragraph context, or quote)
        
        
        Output format:
        Return only valid JSON, structured like this:
        [
            {{
              "category": "Open Methodology & Documentation",
              "results": [
                {{
                  "criterion": "...",
                  "status": "Met" | "Partially Met" | "Not Met" | "Not Applicable",
                  "justification": "..."
                }}
              ]
            }},
            ...
        ]
        Do not include any explanation or commentary outside the JSON.
    """

    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    content = response["message"]["content"]
    try:
        parsed = extract_json_from_response(content)
        return parsed
    except Exception as e:
        print(f"Error parsing response: {e}")
        print("Raw response:")
        print(content)
        return None


# Load PDF content
file_name = "3706468.3706482.pdf"
file_id = os.path.splitext(os.path.basename(file_name))[0]

reader = PdfReader(f"lakproceedings/{file_name}")

# Load checklist
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
    if section_text is None:
        print(f"Section '{name}' not found.")
        continue
    if not section_text:
        print(f"Section '{name}' is empty.")
        continue
    fused_texts.append(section_text)

if fused_texts:
    combined_text = "\n\n".join(fused_texts)
    print("Evaluating combined text from selected sections...")
    result = evaluate_section(combined_text, reproducibility_checklist)
    result_with_id = {
        "id": file_id,
        "results": result
    }


print("Json:")
print(json.dumps(result_with_id, indent=2))

output_path = f"generatedjson/{file_id}_evaluation.json"
with open(output_path, "w") as f:
    json.dump(result_with_id, f , indent=2)

print(f"saved JSON to {output_path}")