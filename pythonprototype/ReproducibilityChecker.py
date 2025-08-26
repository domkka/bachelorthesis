import os
import tkinter
import threading
from google import genai
from google.genai import types
import json
from pypdf import PdfReader
import re
from tkinter import ttk
from tkinter import filedialog,messagebox, simpledialog
import json5

def extract_sections_using_bookmarks(reader: PdfReader):
    """Splits the PDF into sections using its bookmarks."""
    sections = {}
    bookmarks = []

    # get and save bookmarks
    for item in reader.outline:
        if "/Title" in item:
            title = item["/Title"]
            bookmarks.append(title)

    #if pdf has no bookmarks just use full text
    if not bookmarks:
        return {"Full Text": "\n".join(page.extract_text() for page in reader.pages if page.extract_text())}

    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() + "\n"

    # remove all double new lines from text so that headlines will be found and not broken up
    all_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', all_text)
    # Extract text for each section
    for i in range(len(bookmarks)):
        # get current and next bookmark
        title = bookmarks[i]
        next_title = bookmarks[i + 1] if i + 1 < len(bookmarks) else None

        # look for current title in text
        match = re.search(re.escape(title), all_text, re.IGNORECASE)
        if not match:
            print("title not found")
        section_start = all_text[match.end():]

        # look for next title in text and cut off
        if next_title:
            next_match = re.search(re.escape(next_title), section_start, re.IGNORECASE)
            if next_match:
                section_text = section_start[:next_match.start()]
            else:
                section_text = section_start
        else:
            section_text = section_start

        # saves each section
        sections[title] = section_text.strip()

    return sections


def extract_json_from_response(text):
    """parse LLM output to JSON, output start and ends with ```  """
    lines = text.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() =="```":
        lines = lines[:-1]

    json_content = "\n".join(lines)
    return json_content


def generate(pdf_text, checklist, api_key):
    client = genai.Client(
        api_key=api_key,
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

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config
    )

    return response.text

class ReproducibilityChecker:
    def __init__(self, root):
        """Initiate GUI root and variables"""
        self.root = root
        self.root.title("Reproducibility Checker")
        self.root.geometry("1200x600")

        self.file_path = ""
        self.file_label = None
        self.sections = {}
        self.check_vars = {}

        self.api_key = os.environ.get("GEMINI_API_KEY")

        self.build_gui()

    def build_gui(self):
        """ Build Frames, Buttons, Lables"""
        container = ttk.Frame(self.root, padding=10)
        container.grid(row=0, column = 0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container.columnconfigure(0, weight=1)

        frame = ttk.Frame(container, padding=10)
        frame.grid(row=0, column=0, sticky="n")

        self.file_button = ttk.Button(frame, text="Select PDF File", command=self.load_pdf)
        self.file_button.grid(row=0, column=0, pady=5, sticky="ew")

        self.checklist_button = ttk.Button(frame, text="Load Checklist", command=self.load_checklist)
        self.checklist_button.grid(row=0, column=1, pady=5, sticky="ew")

        self.file_label = ttk.Label(frame, text="", foreground="gray")
        self.file_label.grid(row=1, column=0, pady=(0, 10), sticky="ew")

        self.checklist_label = ttk.Label(frame, text="", foreground="gray")
        self.checklist_label.grid(row=1, column=1, pady=(0, 10), sticky="ew")

        self.sections_frame = ttk.LabelFrame(frame, text="Select Sections to evaluate")
        self.sections_frame.grid(row=2, column = 0, pady=10, sticky="ew")

        self.checklist_frame = ttk.LabelFrame(frame,text="Checklist Preview")
        self.checklist_frame.grid(row=2, column=1, columnspan=2, sticky="nsew", pady=10)

        self.checklist_view = tkinter.Text(self.checklist_frame, wrap=tkinter.WORD, height=15)
        self.checklist_view.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.checklist_frame, command=self.checklist_view.yview)
        self.scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        self.checklist_view.config(yscrollcommand=self.scrollbar.set)

        self.eval_button = ttk.Button(frame, text="Run Evaluation", command=self.run_evaluation_thread, state="disabled")
        self.eval_button.grid(row=3, column=0, pady=5, sticky="ew")

        self.key_button = ttk.Button(frame, text="Change API Key", command=self.prompt_api_key, state="normal")
        self.key_button.grid(row=3, column=1, pady=5, sticky="ew")

        self.status_label = ttk.Label(frame, text="",foreground="blue")
        self.status_label.grid(row=4, column=0, pady=5, sticky="ew")

        self.progressbar = ttk.Progressbar(frame, mode="indeterminate")
        self.progressbar.grid(row=5, column=0, pady=5, sticky="ew")
        self.progressbar.grid_remove()

    def prompt_api_key(self):
        """Function to enter API Key"""
        api_key = simpledialog.askstring(
            "API Key Required",
            "Enter your Gemini API Key",
            show="*",
            parent=self.root
        )
        if api_key:
            self.api_key = api_key
        else:
            messagebox.showwarning("Missing Key", "No API key entered.")

    def load_pdf(self):
        """Function to load PDF file and make widgets checkbuttons for selecting sections"""
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

    def load_checklist(self):
        """Function to load and preview checklist"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                self.checklist = json.load(f)
            filename = os.path.basename(file_path)
            self.checklist_label.config(text=f"Loaded checklist: {filename}")

            self.checklist_view.config(state=tkinter.NORMAL)
            self.checklist_view.delete("1.0", tkinter.END)
            formatted_json = json.dumps(self.checklist, indent=4)
            self.checklist_view.insert(tkinter.END, formatted_json)
            self.checklist_view.config(state=tkinter.DISABLED)

            self.eval_button.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load checklist:\n{str(e)}")
            self.checklist = None
            self.checklist_view.insert(tkinter.END, "File not found.")
            self.checklist_view.config(state=tkinter.DISABLED)
            self.eval_button.config(state="disabled")

    def run_evaluation(self):
        """Function to run evaluation, input selcted sections and checklist into generate response, show and save JSON if successfully parsed"""
        selected = [title for title, var in self.check_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("No Selection", "Please select sections.")
            return
        combined_text = "\n\n".join(self.sections[title] for title in selected)
        file_id = os.path.splitext(os.path.basename(self.file_path))[0]

        if not self.checklist:
            messagebox.showwarning("Checklist Missing", "Please load a checklist")
            return
        checklist = self.checklist
        try:
            response=generate(combined_text, checklist, self.api_key)
            responsejson = extract_json_from_response(response)
            parsed = json5.loads(responsejson)
            wrapped_data = {
                "id": file_id,
                "evaluation": parsed
            }

            output_dir = "generatedjson"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{file_id}_evaluation.json")
            with open(output_path, "w") as f:
                json.dump(wrapped_data, f, indent=2)

            messagebox.showinfo("Success", f"Saved JSON to {output_path}")

            self.checklist_view.config(state=tkinter.NORMAL)
            self.checklist_view.delete("1.0", tkinter.END)
            formatted_result = json.dumps(wrapped_data, indent=4)
            self.checklist_view.insert(tkinter.END, formatted_result)
            self.checklist_view.config(state=tkinter.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_evaluation_thread(self):
        """run as thread so program is not frozen during generating and disable buttons while genereating"""
        self.file_button.config(state="disabled")
        self.eval_button.config(state="disabled")
        self.checklist_button.config(state="disabled")
        self.status_label.config(text="Generating response...")
        self.progressbar.grid()
        self.progressbar.start(10)

        thread = threading.Thread(target=self._threaded_evaluation)
        thread.start()

    def _threaded_evaluation(self):
        try:
            self.run_evaluation()
        finally:
            self.root.after(0, self._reset_ui)

    def _reset_ui(self):
        """after eval reset ui components to normal state"""
        self.file_button.config(state="normal")
        self.eval_button.config(state="normal")
        self.checklist_button.config(state="normal")
        self.status_label.config(text="")
        self.progressbar.stop()
        self.progressbar.grid_remove()

if __name__ == "__main__":
    root = tkinter.Tk()
    app = ReproducibilityChecker(root)
    root.mainloop()
