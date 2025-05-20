import ollama
import json
from pypdf import PdfReader
import re

client = ollama.Client()
model = "gemma3:12b"

def extract_json_from_response(text):
    # Find all standalone JSON objects (handles both {...} and ```json...```)
    json_objects = []

    # First try to find ```json ... ``` blocks
    code_blocks = re.findall(r'```(?:json)?\n([\s\S]+?)\n```', text)
    for block in code_blocks:
        try:
            json_objects.append(json.loads(block))
        except json.JSONDecodeError:
            pass  # Not valid JSON, skip

    # Then find all {...} blocks (including multiline)
    brace_blocks = re.findall(r'(?s)\{(?:[^{}]|(?R))*\}', text)
    for block in brace_blocks:
        try:
            json_objects.append(json.loads(block))
        except json.JSONDecodeError:
            pass  # Not valid JSON, skip

    if not json_objects:
        raise ValueError("No valid JSON objects found in the response")

    return json_objects

def evaluate_chunk(document_chunk, checklist):
    checklist_text =""
    for section in checklist:
        category = section['category']
        criteria = "\n".join([
            f"- {item['name']}: {item['description']}"
            for item in section['criteria']
        ])
        checklist_text += f"\nCategory: {category}\n{criteria}\n"

    prompt = f"""
        Evaluate the following document chunk with respect to the checklist criteria below:
        
        Document:
        \"\"\"{document_chunk}\"\"\"
        
        
        Checklist:
        {checklist_text}
        
        
        For each checklist item, provide:
        - `criterion`: the name of the checklist item
        - `status`: one of "Met", "Partially Met", "Not Met", "Not Applicable"
        - `justification`: a short explanation of where or why the criterion is (not) met (e.g., section title, paragraph context, or quote)
        
        
        Output format (as JSON only):
        [
            {{
              "category": "Open Methodology & Documentation",
              "results": [
                {{
                  "criterion": "...",
                  "status": "Met" | "Partially Met" | "Not Met" | "Not Applicable",
                  "justification": "..."
                }},
                ...
              ]
            }},
            ...
        ]
        
        IMPORTANT:
        - Output ONLY valid JSON.
        - Do NOT include markdown (no triple backticks).
        - Do NOT include extra explanation.
    """


    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    content = response["message"]["content"]
    try:
        parsed = extract_json_from_response(content)
        print(json.dumps(parsed, indent=2))
        return parsed
    except Exception as e:
        print(f"Error parsing response: {e}")
        print("Raw response:")
        print(content)
        return None


# Load PDF content
reader = PdfReader("lakproceedings/3706468.3706482.pdf")
paper = ""
for page in reader.pages:
    page_text = page.extract_text()
    if page_text:
        paper += page_text + "\n"

# Find the position of "References" and keep only text before it
references_index = paper.find("References")
if references_index != -1:
    paper = paper[:references_index]

# Load checklist
with open("checklist.json", "r") as file:
    reproducibility_checklist = json.load(file)

chunk_size = len(paper) // 5
chunks = [paper[i:i + chunk_size] for i in range(0, len(paper), chunk_size)]

results = []
for chunk in chunks:
    results.append(evaluate_chunk(chunk, reproducibility_checklist))

final_results = {}
for result in results:
    for category, results_list in result.items():
        if category not in final_results:
            final_results[category] = {"results": []}
        final_results[category]["results"].extend(results_list)

print(json.dumps(final_results, indent=2))