# Jewellery Valuation System

Production-ready demo application for jewellery valuation using a two-stage OpenAI vision pipeline.

## Features

- FastAPI backend with image upload endpoint
- Two-stage VLM workflow
  - Stage 1 visual decomposition
  - Stage 2 strict JSON valuation
- Secure `.env`-based API key loading
- Streamlit frontend for uploads and formatted output
- JSON validation with one corrective retry
- API retry handling and structured logging
- Live Goodreturns gold-rate fetch used as runtime valuation context

## Project Structure

```text
project/
├── app.py
├── config.py
├── local_test.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── prompts/
│   ├── stage1.yml
│   └── stage2.yml
├── services/
│   └── vlm_service.py
├── utils/
│   ├── parser.py
│   └── helpers.py
└── frontend/
    └── streamlit_app.py
```

## Setup

1. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_key_here
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the backend:

```bash
uvicorn app:app --reload
```

4. Run the frontend:

```bash
streamlit run frontend/streamlit_app.py
```

## Local Batch Testing

`local_test.py` runs the same OpenAI-backed service layer used by the FastAPI app, but directly from your terminal. It does not go through the HTTP API.

Set the input in [local_test_args.yml](/Users/saketm10/Documents/jewelary_analysis/local_test_args.yml):

```yaml
input_path: "./WhatsApp Image 2026-03-22 at 21.56.58.jpeg"
recursive: false
```

Then run:

```bash
python local_test.py
```

If you are using the Conda environment created for this project, you can also run:

```bash
~/miniconda3/envs/jewelary_analysis/bin/python local_test.py
```

For a directory batch:

```yaml
input_path: "/path/to/image-directory"
recursive: true
```

Supported image types:

```text
.jpg .jpeg .png .webp .gif
```

What `local_test.py` does:

1. Reads `input_path` from [local_test_args.yml](/Users/saketm10/Documents/jewelary_analysis/local_test_args.yml)
2. Detects whether the path is a single image or a directory
3. Calls the same [analyze_image(...)](/Users/saketm10/Documents/jewelary_analysis/services/vlm_service.py) function used by the backend
4. Writes one output directory per processed image under `output/`
5. Prints a per-image JSON status summary to stdout

Output artifacts per image typically include:

```text
output/<image-name>-<timestamp>/
├── <copied-image>
├── request_metadata.json
├── stage1_attempt1.json
├── stage1_attempt2.json          # only if Stage 1 retry happened
├── stage1_output.json
├── gold_rate_reference.json
├── stage2_attempt1.json
├── stage2_attempt2.json          # only if Stage 2 retry happened
├── analysis_output.json
└── error.json                    # only if a non-recoverable validation failure remained
```

Notes on local test behavior:

- If Stage 1 appears under-segmented, the service automatically retries Stage 1 with a correction note.
- If Stage 2 totals are inconsistent after retries, the system now overrides `total_estimated_value_inr` in code and marks the output with `override_applied`.
- If an image fails for a non-recoverable reason, `local_test.py` exits non-zero and prints an error summary for that file.

## API

### `POST /analyze`

Upload a jewellery image using `multipart/form-data` with the `file` field.

Example:

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@/path/to/jewellery.jpg"
```

## Notes

- The backend fails fast if `OPENAI_API_KEY` is missing.
- The default OpenAI model is `gpt-4.1-mini`, configurable with `OPENAI_MODEL`.
- The response includes the Stage 1 decomposition alongside the structured valuation for demo transparency.
