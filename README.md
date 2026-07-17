# 📖 Book Cover Validation System

Automated computer-vision pipeline that checks book cover submissions against a publisher's layout rules, then routes results through Airtable and email — with **zero manual review** for clean covers.

---

## What it does

Publishers processing large volumes of book cover submissions need each one checked for:

- Text overlapping a **reserved badge/emblem zone** on the cover (critical check — high accuracy required)
- Text sitting inside the safe margins
- Back-cover text alignment
- Image resolution and sharpness

This system automates all four checks with computer vision + OCR, assigns a **PASS** or **REVIEW NEEDED** status with a confidence score, and notifies the submitter by email — with the whole thing triggered by a file simply landing in a Google Drive folder.

---

## Architecture

```
Google Drive folder (ISBN_text.pdf/png)
        │  (n8n polls every minute)
        ▼
n8n: Google Drive Trigger → Download File
        │
        ▼
FastAPI  /analyze  ──────────────────────────┐
        │                                     │
        │  1. Load image / render PDF page    │
        │  2. Run OCR (EasyOCR)                │
        │  3. Validate against layout rules    │
        │  4. Annotate image (colored boxes)   │
        │                                     │
        ▼                                     │
JSON result: status, confidence, issues,       │
             instructions, annotated_image_url │
        │                                     │
        ▼                                     ▼
n8n: Lookup Submitter Info (Airtable)   Streamlit Review UI
        │                            (manual re-check / demo)
        ▼
n8n: IF status == PASS?
   ├── PASS   → Upsert Airtable row → Send PASS email
   └── REVIEW → Upsert Airtable row → Send REVIEW email → wait for resubmission
```

Two front doors (n8n's Drive trigger, and the Streamlit UI) — **one shared FastAPI validation engine** underneath. Same logic, same accuracy, two ways in.

---

## Repo layout

```
app.py               FastAPI app — exposes POST /analyze
config.py            Loads all environment variables (.env)
frontend.py           Streamlit manual review UI
requirements.txt      Python dependencies

vision/
  detector.py         Orchestrates the full pipeline per submission
  ocr.py              EasyOCR wrapper — extracts text + bounding boxes
  rules.py            Cover-spec constants + all validation/scoring logic
  annotate.py         Draws colour-coded boxes on the cover image

utils/
  image_utils.py      Image loading, PDF→image rendering, blur detection

.env.example          Template for required environment variables
```

---

## How the validation actually works

### 1. Front / back cover split
Covers can be uploaded as a single front cover, or a full wraparound spread. `rules.py` checks the aspect ratio — anything wider than 1:1 is treated as a spread and split 50/50 into back (left) and front (right).

### 2. Safe margins & badge zone
Margins and the reserved badge strip are calculated as a **percentage of the real physical cover size**, then applied to whatever pixel resolution the actual upload happens to be. This keeps the checks accurate regardless of the image's DPI.

### 3. Badge overlap — the critical check
Every OCR-detected text box is tested against the badge zone rectangle. If it overlaps at all, the **fraction of the text box that overlaps** is calculated — a text box 90% inside the badge zone is penalized far more heavily than one clipping it by 5%. This is what gives the confidence score real variance instead of a flat pass/fail deduction.

### 4. Continuous, severity-weighted scoring
Every check (resolution, blur, badge overlap, border spacing, back-cover alignment) returns a **penalty proportional to how bad the violation is**, not a fixed deduction. Penalties sum into a single confidence score, clamped between 20–98.

### 5. Status
```
PASS           → zero issues detected
REVIEW NEEDED  → any issue detected, regardless of severity
```

### 6. Annotation
The processed image gets bounding boxes drawn on it:
- 🔴 Red — overlaps the badge zone
- 🟡 Yellow — too close to the border
- 🟢 Green — clean text

Saved to `outputs/` and served as a real, fetchable URL (`BASE_URL/outputs/<isbn>_annotated.png`).

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Configure environment
Copy `.env.example` → `.env` and fill in real values:

```env
AIRTABLE_TOKEN=your_airtable_personal_access_token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Covers
CONFIDENCE_THRESHOLD=0.75
BASE_URL=https://your-domain-or-tunnel.com
FASTAPI_URL=https://your-domain-or-tunnel.com/analyze
```

> `.env` is never committed. Add it to `.gitignore`.

### 3. Run the backend
```bash
uvicorn app:app --reload --port 8000
```

### 4. Run the manual-check UI (optional)
```bash
streamlit run frontend.py
```

### 5. Create n8n workflow
- Google Drive credential + folder ID (Node: *Google Drive Trigger*)
- Airtable credential + base/table (Nodes: *Lookup Submitter Info*, *Create Airtable Record*)
- Gmail credential (Nodes: *Send PASS/REVIEW Email*)

---

## API

### `POST /analyze`

| Field | Type | Description |
|---|---|---|
| `isbn` | form field (string) | Extracted from filename, used as record key & output filename |
| `file` | form file | `.pdf` or `.png` cover |

**Response**
```json
{
  "isbn": "9789373145068",
  "status": "REVIEW NEEDED",
  "confidence": 20,
  "issues": ["❌ Resolution below required cover size [MODERATE]"],
  "instructions": ["Increase image resolution to match required print size and DPI"],
  "annotated_image_url": "https://your-domain.com/outputs/9789373145068_annotated.png"
}
```

---

## File naming convention (required)

All uploads must follow:
```
ISBN_text.ext
e.g. 9789373145068_text.pdf
```
The n8n workflow extracts the ISBN from the filename by splitting on the first underscore. Files that don't follow this convention won't match an existing Airtable record.

---

## Airtable schema (`Covers` table)

| Column | Written by |
|---|---|
| `ISBN` | Matched on (upsert key) |
| `Author Name`, `Author Email` | Pre-populated manually — never overwritten by the workflow |
| `Upload Time` | Google Drive Trigger's file creation time |
| `Detection Time` | Timestamp of the validation run |
| `Status` | `PASS` / `REVIEW NEEDED` |
| `Confidence Score` | 20–98 |
| `Issues` | Comma-separated issue list |
| `Correction Instructions` | Comma-separated fix steps |
| `Revision Number` | Increments by 1 each time that ISBN is processed |
| `Annotated Image URL` | Link to the boxed-and-highlighted cover image |

Records are **upserted** on `ISBN` — reprocessing the same ISBN updates its existing row instead of creating duplicates.

---

## Email notifications

Two branded HTML templates (`email_pass.html`, `email_review.html`), sent via the n8n Gmail node:

- Personalized greeting using the submitter's name from Airtable
- Clear PASS / REVIEW NEEDED status
- Issues shown with the required ❌ text markers
- Step-by-step correction instructions
- Resubmission timeline
- Support contact info

---

## Two ways to submit a cover

| | Google Drive → n8n | Streamlit review UI |
|---|---|---|
| **Purpose** | Production automation | Manual staff re-check / demo |
| **Trigger** | File dropped in watched folder | Manual upload in browser |
| **Output** | Airtable + email, fully automated | Instant visual result in-browser |
| **Backend** | Same `/analyze` endpoint | Same `/analyze` endpoint |

Both call the identical validation engine — one core system, two entry points.

---

## Known limitations / assumptions

- **Wraparound spread detection** is aspect-ratio based (>1:1 = spread); no separate spine strip assumed.
- **Back-cover alignment margin** (2% of edge) isn't always specified by the publisher — used as a reasonable default when no exact figure is given.
- **Resolution check** is a hard 300 DPI floor — typical web-sized test images will fail this by design, since it exists to catch genuinely low-quality uploads.
- OCR confidence filter (`CONFIDENCE_THRESHOLD`) removes low-confidence noise text before validation, which is what keeps the badge-overlap accuracy high.

---

## Testing

To validate: drop a correctly-named test file (`<real ISBN>_text.png`) into the watched Drive folder, then confirm:
1. n8n execution completes without errors
2. Airtable row for that ISBN updates with Status/Confidence/Issues/Annotated URL
3. Email arrives with matching status and correction steps
4. Annotated image at the returned URL shows correctly colour-coded boxes
