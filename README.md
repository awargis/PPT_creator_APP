# Vidyapeeth Test Presentation Studio

A production-oriented, local-first Streamlit application for turning JEE Main, JEE Advanced and NEET UG question-paper PDFs into **reviewable, subject-wise discussion PPTX files**.

> No Gemini/OpenAI API is required by the active pipeline.

## What the application does

```text
Question PDF
    ↓
PyMuPDF native extraction
    ↓
Tesseract OCR fallback (only when native text is insufficient)
    ↓
Page layout / column analysis
    ↓
Exam-profile detection + question-start detection
    ↓
Exam-aware question segmentation + MCQ option grouping
    ↓
Transparent background crop + legibility enhancement
    ↓
Deterministic subject classification
    ↓
Confidence + review screen
    ↓
Uploaded PPT template cloning
    ↓
Subject-wise PPTX + question crops + manifest ZIP
```

## Quick start

### 1. Install Python

Python 3.10–3.12 is recommended.

### 2. Install Python dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Install Tesseract OCR

**Ubuntu/Debian**

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

**Windows**

Install Tesseract OCR and ensure `tesseract.exe` is on PATH. If it is not on PATH, set `pytesseract.pytesseract.tesseract_cmd` in `pipeline/ocr_engine.py` to your local executable.

### 4. Start the application

```bash
streamlit run app.py
```

Then upload:

1. Question-paper PDF
2. Discussion PPT template
3. Optional answer key

The included demo assets are:

- `examples/demo_question_paper.pdf`
- `examples/demo_answer_key.txt`
- `templates/Vidyapeeth_Premium_Discussion_Template.pptx`

## Template contract

The first slide of the uploaded PPTX becomes the visual master.

Supported text tokens:

| Token | Replaced with |
|---|---|
| `#QUESTION` | `Q1`, `Q2`, ... |
| `#SUBJECT` | Physics, Chemistry, Mathematics, etc. |
| `#ANSWER` | Answer-key value |

For exact question-image placement, create a shape on the first slide and rename it:

```text
QUESTION_IMAGE
```

The application replaces that shape with the detected question crop. If it is absent, a safe centered image area is used.

More detail: `docs/TEMPLATE_GUIDE.md`.

## Exam and subject classification

The sidebar supports **Auto-detect** as well as manual override.

- **JEE Main:** modern subject sections that restart numbering at 1 are handled as
  25-question blocks: Physics → Chemistry → Mathematics. The detector does not
  treat `(1) (2) (3) (4)` MCQ options as new questions.
- **NEET UG:** repeated 1–45 subject blocks are handled as Physics → Chemistry →
  Botany → Zoology.
- **JEE Advanced:** no unsafe fixed subject-number mapping is assumed. The system
  uses explicit subject/section headers and sequential question starts, with
  unresolved items marked `Unclassified` for review.
- The first pages are also used for local, explainable exam-type detection
  (JEE Main / JEE Advanced / NEET UG).

This keeps JEE Advanced classification explainable rather than guessing.

## Native extraction vs OCR

Native PDF text is preferred because it provides cleaner characters and precise source coordinates. Tesseract is invoked only when the native text payload is too small, which is typical of scanned/image-only papers.

All downstream crop coordinates are normalized to **rendered-image pixels**, so the crop engine does not mix PDF points and image pixels.

## Output ZIP

The production ZIP contains:

```text
presentations/
  Physics/Physics_Discussion.pptx
  Chemistry/Chemistry_Discussion.pptx

crops/
  Physics/Q001.png
  Chemistry/Q026.png

manifest.json
```

The manifest records subject, answer, confidence, page and crop path for every included question.

## Verification

Run:

```bash
python -m compileall .
pytest -q
flake8 . --select=E9,F63,F7,F82
```

The CI workflow installs `flake8` and `pytest` automatically. If `flake8` is not installed in your local environment, install it with:

```bash
python -m pip install flake8 pytest
```

## Current engineering scope

The project is deliberately deterministic and reviewable. Question boundaries are
based on detected question starts, not option labels, so a complete MCQ (question
+ all options) becomes one crop. Questions that continue onto another PDF page
are stitched into one crop. Near-white paper is converted to transparency so
the source question sits cleanly on a premium PPT background.

Unusual multi-page layouts, heavily graphical scans, OCR errors, or non-standard
JEE Advanced section numbering can still require human review. The UI therefore
exposes confidence and manual correction before PPT export.
