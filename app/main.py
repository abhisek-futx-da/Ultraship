"""
Ultra Doc-Intelligence - Main FastAPI Application
AI-powered logistics document intelligence system with RAG capabilities
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os

from app.document_processor import DocumentProcessor
from app.rag_system import RAGSystem
from app.extractor import StructuredExtractor
from app.guardrails import Guardrails

app = FastAPI(
    title="Ultra Doc-Intelligence",
    description="AI-powered logistics document intelligence system",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
doc_processor = DocumentProcessor()
rag_system = RAGSystem()
extractor = StructuredExtractor()
guardrails = Guardrails()

# Store current document context
current_document_id = None
current_document_text = None


class QuestionRequest(BaseModel):
    question: str
    document_id: Optional[str] = None


class ExtractRequest(BaseModel):
    document_id: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path, "r") as f:
        return f.read()


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a logistics document (PDF, DOCX, or TXT)
    Returns document_id for subsequent queries
    """
    global current_document_id, current_document_text
    
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Process document
        document_id, chunks, text = doc_processor.process_document(
            content=content,
            filename=file.filename,
            file_type=file_ext
        )
        
        # Create embeddings and store in vector index
        rag_system.index_document(document_id, chunks, text)
        
        current_document_id = document_id
        current_document_text = text
        
        return {
            "status": "success",
            "document_id": document_id,
            "filename": file.filename,
            "chunks_count": len(chunks),
            "message": "Document processed and indexed successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded document using RAG
    Returns answer, source text, and confidence score
    """
    global current_document_id
    
    try:
        document_id = request.document_id or current_document_id
        
        if not document_id:
            raise HTTPException(
                status_code=400,
                detail="No document uploaded. Please upload a document first."
            )
        
        # Retrieve relevant context using RAG
        relevant_chunks, similarity_scores = rag_system.retrieve(
            query=request.question,
            document_id=document_id,
            top_k=3
        )
        
        # Apply guardrails
        guardrail_result = guardrails.check(
            question=request.question,
            chunks=relevant_chunks,
            similarity_scores=similarity_scores
        )
        
        if not guardrail_result["allowed"]:
            return {
                "answer": guardrail_result["message"],
                "source_text": [],
                "confidence_score": 0.0,
                "guardrail_triggered": True,
                "reason": guardrail_result["reason"]
            }
        
        # Generate answer using LLM with retrieved context
        answer, confidence = rag_system.generate_answer(
            question=request.question,
            context_chunks=relevant_chunks,
            similarity_scores=similarity_scores
        )
        
        # Format source text with metadata
        source_text = [
            {
                "text": chunk["text"],
                "similarity": float(score),
                "chunk_index": chunk.get("index", 0)
            }
            for chunk, score in zip(relevant_chunks, similarity_scores)
        ]
        
        return {
            "answer": answer,
            "source_text": source_text,
            "confidence_score": float(confidence),
            "guardrail_triggered": False
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.post("/extract")
async def extract_structured_data(request: ExtractRequest):
    """
    Extract structured shipment data from the document
    Returns JSON with shipment fields or nulls if missing
    """
    global current_document_id, current_document_text
    
    try:
        document_id = request.document_id or current_document_id
        
        if not document_id:
            raise HTTPException(
                status_code=400,
                detail="No document uploaded. Please upload a document first."
            )
        
        # Get document text (from vector store or in-memory fallback)
        try:
            document_text = rag_system.get_document_text(document_id)
        except ValueError:
            # Document not in index (e.g. server restarted); try server-side fallback
            if document_id == current_document_id and current_document_text:
                document_text = current_document_text
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Document not found. Please upload the document again."
                )
        
        if not (document_text or document_text.strip()):
            raise HTTPException(
                status_code=400,
                detail="Document has no extractable text."
            )
        
        # Extract structured data using LLM or rule-based fallback
        try:
            extracted_data = extractor.extract(document_text)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Extraction failed: {str(e)}"
            )
        
        # Ensure we always return a dict (serializable)
        if not isinstance(extracted_data, dict):
            extracted_data = {}
        
        return {
            "status": "success",
            "data": extracted_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting data: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Ultra Doc-Intelligence"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
