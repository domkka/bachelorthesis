import ollama
import json
from pypdf import PdfReader
import re

client = ollama.Client()
model = "gemma3:27b"

def extract_json_from_response(text):
    # Find JSON enclosed in ```json ... ``` or just {...}
    json_match = re.search(r"```json\s*(\{.*?})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Fallback: try to find the first {...} block
        json_match = re.search(r"(\{.*})", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            raise ValueError("No JSON object found in the response")
    return json.loads(json_str)

def evaluate_study(document, checklist):
    prompt_sections = []

    for section in checklist:
        category = section['category']
        criteria_text = "\n".join(
            [f"- {item['name']}: {item['description']}" for item in section['criteria']]
        )

        prompt = f"""
            Category: {category}

            Evaluate the following document with respect to the checklist criteria below:

            Document:
            \"\"\"{document}\"\"\"

            Checklist:
            {criteria_text}

            For each checklist item, provide:
            - `criterion`: the name of the checklist item
            - `status`: one of "Met", "Partially Met", "Not Met", "Not Applicable"
            - `justification`: a short explanation of where or why the criterion is (not) met (e.g., section title, paragraph context, or quote)

            Output format:
            {{
              "category": "{category}",
              "results": [
                {{
                  "criterion": "...",
                  "status": "Met" | "Partially Met" | "Not Met" | "Not Applicable",
                  "justification": "..."
                }},
                ...
              ]
            }}
            """
        prompt_sections.append(prompt)

    results = []

    for prompt in prompt_sections:
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
        )
        content = response["message"]["content"]
        try:
            parsed = extract_json_from_response(content)
            results.append(parsed)
        except Exception as e:
            print(f"Error parsing response: {e}")
            print("Raw response:")
            print(content)

    # Print results
    for section_result in results:
        print(f"\n=== {section_result['category']} ===")
        for item in section_result['results']:
            print(f"- {item['criterion']}: {item['status']}")
            print(f"  Justification: {item['justification']}")

# Load PDF content
reader = PdfReader("lakproceedings/3706468.3706470.pdf")
paper = ""

for page in reader.pages:
    page_text = page.extract_text()
    if page_text:
        paper += page_text + "\n"

# Load checklist
with open("checklist.json", "r") as file:
    checklist = json.load(file)

# Run evaluation
evaluate_study(paper, checklist)