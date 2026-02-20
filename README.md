# 🚚 Ultra Doc-Intelligence

**AI-powered Logistics Document Intelligence System with RAG capabilities**

A Production-Ready POC system that allows users to upload logistics documents (BOL, Rate Confirmations, Invoices, etc.) and interact with them using natural language questions. Built with FastAPI, RAG (Retrieval-Augmented Generation), and advanced guardrails to ensure grounded, accurate answers.

---

## 📌 Submission

| Requirement | Link |
|-------------|------|
| **GitHub repository** | [https://github.com/abhisek-futx-da/ultra-doc-intelligence](https://github.com/abhisek-futx-da/ultra-doc-intelligence) |
| **Hosted UI** | [https://ultra-doc-intelligence.onrender.com](https://ultra-doc-intelligence.onrender.com) *(deploy from GitHub to get your live URL)* |
| **Run locally** | See [Installation](#installation) and [Usage](#usage) below. |

**One-click deploy (Hosted UI):** After pushing this repo to your GitHub, [deploy on Render](https://render.com/deploy?repo=https://github.com/abhisek-futx-da/ultra-doc-intelligence) — your app will be live at `https://<your-service-name>.onrender.com`.

---

## 📋 Table of Contents

- [Submission](#-submission)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [System Design Details](#system-design-details)
- [Evaluation Criteria Coverage](#evaluation-criteria-coverage)
- [Future Improvements](#future-improvements)

---

## ✨ Features

### Core Features
- ✅ **Document Upload & Processing**: Supports PDF, DOCX, and TXT formats
- ✅ **Intelligent Chunking**: Sentence-aware chunking with overlap for context preservation
- ✅ **RAG System**: Vector-based retrieval with semantic search
- ✅ **Natural Language Q&A**: Ask questions about uploaded documents
- ✅ **Guardrails**: Multiple safety checks to prevent hallucinations
- ✅ **Confidence Scoring**: Multi-factor confidence calculation
- ✅ **Structured Extraction**: Extract shipment data as JSON
- ✅ **Minimal UI**: Clean, user-friendly web interface

### Advanced Features
- **Grounded Answers**: Answers only from document context
- **Source Attribution**: Shows source text with similarity scores
- **Fallback Mechanisms**: Rule-based extraction if LLM unavailable
- **Error Handling**: Comprehensive error handling and user feedback

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS)                    │
│              Document Upload | Q&A | Extraction              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Upload     │  │     Ask      │  │   Extract    │      │
│  │   Endpoint   │  │   Endpoint   │  │   Endpoint   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Document Processing Pipeline                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Parser     │→ │   Chunker    │→ │  Embeddings  │     │
│  │ (PDF/DOCX)   │  │ (Intelligent)│  │  (Vector DB) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG System                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Vector     │  │   Retrieval  │  │   LLM        │     │
│  │   Search     │→ │   (Top-K)    │→ │   Generation │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Guardrails & Confidence Scoring                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Similarity   │  │   Chunk      │  │   Answer     │     │
│  │  Threshold   │  │   Quality    │  │   Grounding  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

1. **Document Processor** (`document_processor.py`)
   - Parses PDF, DOCX, TXT files
   - Intelligent sentence-aware chunking
   - Overlap strategy for context preservation

2. **RAG System** (`rag_system.py`)
   - Embeddings using Sentence Transformers
   - Vector similarity search (cosine similarity)
   - LLM integration via OpenRouter API
   - In-memory vector store (scalable to FAISS/Pinecone)

3. **Guardrails** (`guardrails.py`)
   - Similarity threshold checks
   - Chunk quality validation
   - Answer grounding verification

4. **Structured Extractor** (`extractor.py`)
   - LLM-based extraction with fallback
   - Rule-based regex patterns
   - JSON schema validation

---

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for APIs
- **Python 3.8+**: Core language
- **Sentence Transformers**: Embedding generation
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX text extraction
- **NumPy**: Vector operations

### AI/ML
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **LLM**: OpenRouter API (supports multiple models)
- **Vector Search**: Cosine similarity

### Frontend
- **HTML/CSS/JavaScript**: Minimal, responsive UI
- **No Framework**: Vanilla JS for simplicity

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd "ultraship 2"
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables (optional)**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

   **Note**: The system works without an API key using fallback methods, but LLM-based answers will be limited.

---

## 🚀 Usage

### Running Locally

1. **Start the server**
   ```bash
   python -m app.main
   # Or
   uvicorn app.main:app --reload
   ```

2. **Open your browser**
   Navigate to: `http://localhost:8000`

3. **Upload a document**
   - Drag & drop or click to upload a PDF, DOCX, or TXT file
   - Wait for processing confirmation

4. **Ask questions**
   - Type questions in the input field
   - Click "Ask Question" or press Enter
   - View answer, confidence score, and source text

5. **Extract structured data**
   - Click "Extract Shipment Data"
   - View extracted fields in a table

### Sample Documents
Test with the provided sample documents in `sample_documents/`:
- `BOL53657_billoflading.pdf`
- `LD53657-Carrier-RC.pdf`
- `LD53657-Shipper-RC.pdf`

---

## 🔌 API Endpoints

### `POST /upload`
Upload and process a document.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (PDF, DOCX, or TXT)

**Response:**
```json
{
  "status": "success",
  "document_id": "abc123...",
  "filename": "document.pdf",
  "chunks_count": 15,
  "message": "Document processed and indexed successfully"
}
```

### `POST /ask`
Ask a question about the uploaded document.

**Request:**
```json
{
  "question": "What is the carrier rate?",
  "document_id": "abc123..."  // Optional, uses current if omitted
}
```

**Response:**
```json
{
  "answer": "The carrier rate is $1,250.00 USD.",
  "source_text": [
    {
      "text": "Rate: $1,250.00 USD...",
      "similarity": 0.85,
      "chunk_index": 3
    }
  ],
  "confidence_score": 0.87,
  "guardrail_triggered": false
}
```

### `POST /extract`
Extract structured shipment data.

**Request:**
```json
{
  "document_id": "abc123..."  // Optional
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "shipment_id": "BOL53657",
    "shipper": "ABC Logistics",
    "consignee": "XYZ Corp",
    "pickup_datetime": "2024-01-15 08:00",
    "delivery_datetime": "2024-01-20 17:00",
    "equipment_type": "Dry Van",
    "mode": "TL",
    "rate": 1250.00,
    "currency": "USD",
    "weight": 45000,
    "carrier_name": "Fast Freight Inc"
  }
}
```

### `GET /health`
Health check endpoint.

---

## 🔍 System Design Details

### Chunking Strategy

**Approach**: Sentence-aware chunking with overlap

1. **Sentence Splitting**: Text is split by sentence boundaries (`.`, `!`, `?`)
2. **Sliding Window**: Chunks of ~500 words with 100-word overlap
3. **Context Preservation**: Overlap ensures important context isn't lost at boundaries
4. **Metadata**: Each chunk stores index, document_id, and character positions

**Rationale**: 
- Prevents breaking context mid-sentence
- Overlap ensures retrieval doesn't miss boundary information
- Balances chunk size (context) vs. retrieval precision

### Retrieval Method

**Approach**: Vector similarity search with cosine similarity

1. **Embedding Generation**: 
   - Query and chunks embedded using `all-MiniLM-L6-v2`
   - 384-dimensional vectors
2. **Similarity Calculation**: Cosine similarity between query and chunk embeddings
3. **Top-K Retrieval**: Returns top 3 most similar chunks
4. **Scoring**: Similarity scores used for confidence calculation

**Rationale**:
- Semantic search captures meaning, not just keywords
- Top-K ensures multiple context sources
- Cosine similarity is efficient and effective for embeddings

### Guardrails Approach

**Multi-Layer Guardrails**:

1. **Similarity Threshold** (0.3 minimum)
   - Rejects answers if max similarity < threshold
   - Prevents answering from irrelevant context

2. **Chunk Quality Check**
   - Ensures minimum number of chunks retrieved
   - Validates chunks aren't too short (noise filtering)

3. **Answer Grounding Validation**
   - Checks if answer contains words from context
   - Detects phrases indicating missing information
   - Word overlap ratio validation

4. **Explicit Refusal**
   - Returns "Not found in document" when context missing
   - Clear messaging when guardrails trigger

**Rationale**: Multiple layers catch different failure modes, ensuring high-quality, grounded answers.

### Confidence Scoring Method

**Multi-Factor Confidence Calculation**:

```python
confidence = (
    avg_similarity * 0.6 +           # Base from retrieval
    agreement_boost * 0.2 +           # Chunk agreement
    coverage_boost                    # Answer coverage
) * penalty                           # Missing info penalty
```

**Factors**:
1. **Average Similarity** (60% weight): Mean of top-K similarity scores
2. **Chunk Agreement** (20% weight): Low std = high agreement = boost
3. **Answer Coverage** (20% weight): Answer contains context terms
4. **Penalty**: Applied if answer indicates missing info

**Output**: Normalized score 0.0-1.0, categorized as:
- High (≥0.7): Green
- Medium (0.4-0.7): Yellow
- Low (<0.4): Red

---

## ✅ Evaluation Criteria Coverage

| Criterion | Implementation |
|-----------|---------------|
| **Retrieval Grounding Quality** | ✅ Vector similarity search with top-K retrieval, source attribution |
| **Extraction Accuracy** | ✅ LLM + rule-based fallback, JSON schema validation |
| **Guardrail Effectiveness** | ✅ Multi-layer guardrails (similarity, quality, grounding) |
| **Confidence Scoring Logic** | ✅ Multi-factor scoring with transparency |
| **Code Structure** | ✅ Modular design, separation of concerns, clean code |
| **End-to-End Usability** | ✅ Simple UI, clear error messages, example questions |
| **Practical AI Engineering** | ✅ Fallback mechanisms, error handling, scalability considerations |

---

## 🚧 Failure Cases & Handling

### Document Processing Failures
- **Unsupported format**: Returns 400 error with allowed types
- **Corrupted file**: Catches exceptions, returns user-friendly error
- **Empty document**: Validates text extraction, returns error

### Retrieval Failures
- **No relevant chunks**: Guardrail triggers, returns "Not found"
- **Low similarity**: Guardrail rejects, explains low relevance
- **Missing document**: Returns 400 error with clear message

### LLM API Failures
- **API unavailable**: Falls back to rule-based extraction
- **Timeout**: Catches exception, uses fallback
- **Invalid response**: Validates JSON, handles gracefully

### Extraction Failures
- **Missing fields**: Returns null for missing fields (as required)
- **Parsing errors**: Falls back to rule-based extraction
- **Invalid JSON**: Validates and corrects if possible

---

## 🔮 Future Improvements

### Short-Term
1. **Vector Database**: Replace in-memory store with FAISS or Pinecone
2. **Batch Processing**: Support multiple document uploads
3. **Document Management**: List, delete, switch between documents
4. **Export**: Download extracted data as CSV/JSON

### Medium-Term
1. **Advanced Chunking**: 
   - Domain-aware chunking (tables, sections)
   - Hierarchical chunking for large documents
2. **Enhanced Retrieval**:
   - Hybrid search (keyword + semantic)
   - Re-ranking with cross-encoder
3. **Better LLM Integration**:
   - Support for local models (Ollama)
   - Streaming responses
   - Model selection UI

### Long-Term
1. **Multi-Document Q&A**: Query across multiple documents
2. **Document Comparison**: Compare fields across documents
3. **Custom Extraction Schemas**: User-defined extraction templates
4. **Analytics Dashboard**: Usage statistics, accuracy metrics
5. **Authentication**: User accounts, document privacy
6. **API Rate Limiting**: Production-ready rate limiting

---

## 📝 Notes

- **LLM API Key**: Optional but recommended for best results. System works with fallback methods.
- **Performance**: First document processing may take 10-30 seconds (embedding generation). Subsequent queries are fast.
- **Scalability**: Current implementation uses in-memory storage. For production, integrate with vector DB (FAISS, Pinecone, Weaviate).

---

## 👤 Author

**Abhishek Jindal**
- Data Scientist | AI/ML Engineer
- Built with expertise in FastAPI, Python, ML/AI, and production systems

---

## 📄 License

This project is a POC for evaluation purposes.

---

**Built with ❤️ using FastAPI, RAG, and modern AI engineering practices**
