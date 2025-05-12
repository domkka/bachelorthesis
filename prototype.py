import requests
import json

def evaluate_study(materials, checklist):
    prompt = f"""
    Evaluate the study based on the checklist:
    Checklist: {json.dumps(checklist, indent=2)}
    Materials: {materials}
    Output in JSON format with criterion, status, and explanation.
    """
    response = requests.post(
        "https://api.x.ai/grok3",  # Hypothetical endpoint
        headers={"Authorization": "Bearer YOUR_API_KEY"},
        json={"prompt": prompt}
    )
    return response.json()

materials = {
    "paper": "Extracted text from PDF...",
    "code": "GitHub link: https://github.com/example/repo",
    "dataset": "Dataset description..."
}

with open("checklist.json", "r") as file:
    checklist = json.load(file)

result = evaluate_study(materials, checklist)
print(json.dumps(result, indent=2))