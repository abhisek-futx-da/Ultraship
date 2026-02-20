"""
Document Processor Module
Handles parsing, chunking, and text extraction from various document formats
"""

import os
import hashlib
from typing import List, Dict, Tuple
import PyPDF2
from docx import Document
import io


class DocumentProcessor:
    """Processes documents (PDF, DOCX, TXT) and creates intelligent chunks"""
    
    def __init__(self):
        self.upload_dir = "uploads"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def process_document(
        self, 
        content: bytes, 
        filename: str, 
        file_type: str
    ) -> Tuple[str, List[Dict], str]:
        """
        Process document and return document_id, chunks, and full text
        
        Args:
            content: File content as bytes
            filename: Original filename
            file_type: File extension (.pdf, .docx, .txt)
        
        Returns:
            Tuple of (document_id, chunks, full_text)
        """
        # Extract text based on file type
        if file_type == '.pdf':
            text = self._extract_pdf_text(content)
        elif file_type == '.docx':
            text = self._extract_docx_text(content)
        elif file_type == '.txt':
            text = content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Generate document ID
        document_id = self._generate_document_id(content, filename)
        
        # Create intelligent chunks
        chunks = self._chunk_text(text, document_id)
        
        return document_id, chunks, text
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting PDF text: {str(e)}")
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            docx_file = io.BytesIO(content)
            doc = Document(docx_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting DOCX text: {str(e)}")
    
    def _generate_document_id(self, content: bytes, filename: str) -> str:
        """Generate unique document ID"""
        hash_input = content + filename.encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()
    
    def _chunk_text(
        self, 
        text: str, 
        document_id: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100
    ) -> List[Dict]:
        """
        Intelligently chunk text with overlap for better context preservation
        
        Strategy:
        - Split by sentences first to avoid breaking context
        - Use sliding window with overlap
        - Preserve document structure (paragraphs, sections)
        """
        if not text:
            return []
        
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence.split())
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "index": len(chunks),
                    "document_id": document_id,
                    "char_start": text.find(chunk_text) if chunk_text in text else 0,
                    "char_end": 0  # Will be calculated if needed
                })
                
                # Start new chunk with overlap (keep last few sentences)
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "index": len(chunks),
                "document_id": document_id,
                "char_start": text.find(chunk_text) if chunk_text in text else 0,
                "char_end": 0
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple heuristics"""
        import re
        # Split by sentence endings, but preserve abbreviations
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out empty sentences
        return [s.strip() for s in sentences if s.strip()]
