import os
import tkinter

from google import genai
from google.genai import types
import json
from pypdf import PdfReader
import re
from tkinter import ttk
from tkinter import filedialog,messagebox

def extract_sections_using_bookmarks(reader: PdfReader):
    """Splits the PDF into sections using its bookmarks."""
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

        match = re.search(re.escape(title), all_text, re.IGNORECASE)
        if not match:
            print("title not found")
        section_start = all_text[match.end():]

        if next_title:
            next_match = re.search(re.escape(next_title), section_start, re.IGNORECASE)
            if next_match:
                section_text = section_start[:next_match.start()]
            else:
                section_text = section_start
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

class ReproducibilityChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Reproducibility Checker")
        self.root.geometry("600x600")

        self.file_path = ""
        self.file_label = None
        self.sections = {}
        self.check_vars = {}

        self.build_gui()

    def build_gui(self):
        container = ttk.Frame(self.root, padding=10)
        container.grid(row=0, column = 0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container.columnconfigure(0, weight=1)

        frame = ttk.Frame(container, padding=10)
        frame.grid(row=0, column=0, sticky="n")

        ttk.Button(frame, text="Select PDF File", command=self.load_pdf).grid(row=0, column=0, pady=5, sticky="ew")

        self.file_label = ttk.Label(frame, text="", foreground="gray")
        self.file_label.grid(row=1, column=0, pady=(0, 10), sticky="ew")

        self.sections_frame = ttk.LabelFrame(frame, text="Select Sections to evaluate")
        self.sections_frame.grid(row=2, column = 0, pady=10, sticky="ew")

        ttk.Button(frame, text="Run Evaluation", command=self.run_evaluation).grid(row=3, column=0, pady=5, sticky="ew")

    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return
        self.file_path = file_path
        filename = os.path.basename(self.file_path)
        self.file_label.config(text=f"Selected file: {filename}")
        reader = PdfReader(file_path)
        self.sections = extract_sections_using_bookmarks(reader)

        for widget in self.sections_frame.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        for i, title in enumerate(self.sections):
            var = tkinter.BooleanVar()
            chk = ttk.Checkbutton(self.sections_frame, text=title, variable=var)
            chk.grid(row=i, column=0, sticky="w")
            self.check_vars[title] = var

    def run_evaluation(self):
        selected = [title for title, var in self.check_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("No Selection", "Please select sections.")
            return
        combined_text = "\n\n".join(self.sections[title] for title in selected)
        file_id = os.path.splitext(os.path.basename(self.file_path))[0]

        with open("checklist.json", "r") as file:
            checklist = json.load(file)

        try:
            response=generate(combined_text, checklist)
            responsejson = extract_json_from_response(response)
            parsed = json.loads(responsejson)
            wrapped_data = {
                "id": file_id,
                "evaluation": parsed
            }
            output_path = f"generatedjson/{file_id}_evaluation.json"
            with open(output_path, "w") as f:
                json.dump(wrapped_data, f, indent=2)
            print(f"saved JSON to {output_path}")

            messagebox.showinfo("Success", f"Saved JSON to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tkinter.Tk()
    app = ReproducibilityChecker(root)
    root.mainloop()
