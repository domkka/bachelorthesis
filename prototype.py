import ollama
import json
from pypdf import PdfReader


client = ollama.Client()
model = "gemma3:27b"

def evaluate_study(document, checklist):
    prompt = f"""
        Evaluate the following document using this checklist:
        {json.dumps(checklist, indent=2)}
        . 
        For each checklist item, provide:
        - `criterion`: the name or summary of the checklist item
        - `status`: one of "Met", "Partially Met", or "Not Met"


        Paper:
        \"\"\"
        {document}
        \"\"\"

        Output format:
        [
          {{
            "criterion": "...",
            "status": "Met" | "Partially Met" | "Not Met"
          }},
          ...
        ]
        """

    prompt2 = f"""
    Document: 
    \"\"\"
    {document}
    \"\"\"
    
    
    Answer the question for the given document:
    
    
    Question: Is there a step-by-step description of the experimental design?
    
    Output format:
    "yes" | "no" | "na"
    """

    response = client.generate(model=model, prompt=prompt2, options={"temperature":0})

    print(response.response)

# Load PDF content
reader = PdfReader("lakproceedings/3706468.3706470.pdf")
paper = ""
second_page = reader.pages[1].extract_text()
third_page = reader.pages[2].extract_text()

sec_third_pages = second_page + "\n" + third_page

for page in reader.pages:
    page_text = page.extract_text()
    if page_text:
        paper += page_text + "\n"

# Load checklist
with open("checklist.json", "r") as file:
    checklist = json.load(file)

# Run evaluation
evaluate_study(sec_third_pages, checklist)