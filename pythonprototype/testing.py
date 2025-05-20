import json
import re
from pypdf import PdfReader


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

# Load PDF
reader = PdfReader("lakproceedings/3706468.3706470.pdf")

# Split into sections using bookmarks
sections = extract_sections_using_bookmarks(reader)
print(f"Extracted sections: {list(sections.keys())}")
for section_name, section_text in sections.items():
    if section_name == "References":
        print("Skipping References")
        continue
    if not section_text:
        print("empty section")
        continue
    print("\n")
    print(f"Section name: {section_name}")
    print(f"Section text: {section_text}")
    print("\n")

