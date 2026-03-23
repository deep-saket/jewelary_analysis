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

Set the input in [local_test_args.yml](/Users/saketm10/Documents/jewelary_analysis/local_test_args.yml):

```yaml
input_path: "./WhatsApp Image 2026-03-22 at 21.56.58.jpeg"
recursive: false
```

Then run:

```bash
python local_test.py
```

For a directory batch:

```yaml
input_path: "/path/to/image-directory"
recursive: true
```

Each image creates its own subdirectory inside `output/` with the copied source image, request metadata, stage outputs, and the final JSON result.

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
