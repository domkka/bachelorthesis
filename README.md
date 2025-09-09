# An Automatic Reproducibility Pipeline for the Learning AnalyticsAcademic Community

Welcome to my Repository for my Bachelor Thesis "An Automatic Reproducibility Pipeline for the Learning Analytics Academic Community".
Here you can find the Thesis, Presentation and all Code for the Prototype, Visualization and Scoring.

## Structure

The Thesis and Presentation can be found at /Bachelorthesis_DK.pdf and /Presentation_DK.odp
Under /study/ the Study process and Survey can be found, aswell as all anonymized Feedback of the participants.
Code for Visualization of the results can be found in /visualization/

The directory /pythonprototype/ contains the Code for the ReproducibilityChecker.py prototype, aswell as the jsonscorer.py.
Additionally the checklist.json is saved here. Also all papers used can be found at /pythonprototype/lakproceedings, and all evaluated checklists under /pythonprototype/generatedjson and pythonprototype/generatedjson_study.

An alternative approach for handling differently strucutred PDF-Files can be found under /pythonprototype/altchecker

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install all requirements.

```bash
pip install -r requirements.txt
```

## Usage

To use the Prototype a Google Gemini API key is needed, you can generate it here: https://aistudio.google.com/apikey
It can be saved as an environment Variable "GEMINI_API_KEY" or inserted after clicking "Change API Key".

Click "Select PDF File" and select a paper. After that you can select the sections that should be used for the evaluation.
Click "Load Checklist" to select the checklist.json.
Click "Run Evaluation" to start the evaluation by making an API request to the LLM Gemma 3.

The output will be parsed as json and can then be found in /generatedjson.
You can see the file in the preview window or open the json and check the evaluation.

## License

[MIT](https://choosealicense.com/licenses/mit/)
