# AI Exam Evaluation System

Production-ready system for automated evaluation of student exam papers using a **single LLM** (Llama 4 Maverick via Groq API) for both OCR and evaluation.

## Features

- **Single LLM for Everything**: Uses Llama 4 Maverick for text extraction AND evaluation
- **No External OCR Dependencies**: No Tesseract required - LLM handles handwritten text
- **Robust Rate Limit Handling**: Automatically waits and retries on TPM/RPM limits
- **Smart Scoring**: Strict (1-mark/True-False) and Liberal (multi-mark) evaluation modes
- **Drop-Lowest Logic**: Discards lowest-scoring question when student answers all 3 in a section

## Prerequisites

1. **Python 3.9+** for backend
2. **Node.js 18+** for frontend  
3. **Groq API Key** from [groq.com](https://console.groq.com)

> ✅ **No Tesseract required!** The LLM handles all text extraction.

## Quick Start

### 1. Backend Setup

```bash
cd paper_ai/backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key in .env
# GROQ_API_KEY=your_key_here
```

### 2. Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd paper_ai/frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Configuration

Edit `backend/app/config/config.yaml`:

```yaml
llm:
  provider: "groq"
  model: "meta-llama/llama-4-maverick-17b-128e-instruct"
  base_url: "https://api.groq.com/openai/v1"
  api_key: "${GROQ_API_KEY}"
  timeout_seconds: 120

ocr:
  engine: "llm"  # Uses same LLM for text extraction
  dpi: 200
```

## Rate Limit Handling

The system automatically handles Groq's TPM (tokens per minute) limits:

- **429 errors**: Waits for `retry-after` header or uses exponential backoff
- **Max retries**: 10 attempts with increasing delays
- **Auto-resume**: Continues from where it left off after rate limit ends

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload 3 PDFs, returns job_id |
| GET | `/api/status/{job_id}` | Get job status |
| GET | `/api/result/{job_id}` | Get evaluation result |

## Output Format

```json
{
  "student_id": "7376222AD184",
  "sections": {
    "A": {
      "retained_questions": ["A1", "A2"],
      "discarded_questions": ["A3"],
      "questions": { ... },
      "section_total": 9
    }
  },
  "grand_total": 45,
  "overall_feedback": "Strong understanding."
}
```

## License

MIT
# Paper_AI_Evaluation-BIT-
# Paper_AI_Evaluation-BIT-
