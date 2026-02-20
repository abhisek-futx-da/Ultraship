"""
RAG (Retrieval-Augmented Generation) System
Handles embeddings, vector search, and answer generation
"""

import os
import json
from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import requests


class RAGSystem:
    """RAG system for document retrieval and answer generation"""
    
    def __init__(self):
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384
        
        # In-memory vector store (can be replaced with FAISS, Pinecone, etc.)
        self.vector_store: Dict[str, Dict] = {}
        
        # LLM API configuration (using OpenRouter as per resume experience)
        self.llm_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.llm_api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.llm_model = "openai/gpt-3.5-turbo"  # Can be changed to other models
    
    def index_document(self, document_id: str, chunks: List[Dict], full_text: str):
        """
        Create embeddings for document chunks and store in vector index
        """
        if not chunks:
            return
        
        # Generate embeddings for all chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.encode(chunk_texts, show_progress_bar=False)
        
        # Store in vector index
        self.vector_store[document_id] = {
            "chunks": chunks,
            "embeddings": embeddings.tolist(),
            "full_text": full_text
        }
    
    def retrieve(
        self, 
        query: str, 
        document_id: str, 
        top_k: int = 3
    ) -> Tuple[List[Dict], List[float]]:
        """
        Retrieve relevant chunks using vector similarity search
        
        Returns:
            Tuple of (relevant_chunks, similarity_scores)
        """
        if document_id not in self.vector_store:
            raise ValueError(f"Document {document_id} not found in index")
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
        
        # Get document embeddings
        doc_data = self.vector_store[document_id]
        chunk_embeddings = np.array(doc_data["embeddings"])
        
        # Calculate cosine similarity
        similarities = self._cosine_similarity(
            query_embedding.reshape(1, -1),
            chunk_embeddings
        )[0]
        
        # Get top-k most similar chunks
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        relevant_chunks = [doc_data["chunks"][idx] for idx in top_indices]
        similarity_scores = [float(similarities[idx]) for idx in top_indices]
        
        return relevant_chunks, similarity_scores
    
    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict],
        similarity_scores: List[float]
    ) -> Tuple[str, float]:
        """
        Generate answer using LLM with retrieved context
        
        Returns:
            Tuple of (answer, confidence_score)
        """
        # Combine context chunks
        context = "\n\n".join([chunk["text"] for chunk in context_chunks])
        
        # Create prompt for LLM
        prompt = f"""You are an AI assistant that answers questions about logistics documents.
Answer ONLY based on the provided document context. If the answer is not in the context, say "I cannot find this information in the document."

Document Context:
{context}

Question: {question}

Answer:"""
        
        # Call LLM API
        if self.llm_api_key:
            answer = self._call_llm_api(prompt)
        else:
            # Fallback to simple extraction if no API key
            answer = self._simple_answer_extraction(question, context_chunks)
        
        # Calculate confidence score based on similarity and context quality
        confidence = self._calculate_confidence(similarity_scores, context_chunks, answer)
        
        return answer, confidence
    
    def _call_llm_api(self, prompt: str) -> str:
        """Call OpenRouter LLM API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Low temperature for factual answers
                "max_tokens": 500
            }
            
            response = requests.post(self.llm_api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        
        except Exception as e:
            # Fallback if API fails
            return f"Error calling LLM API: {str(e)}. Using fallback method."
    
    def _simple_answer_extraction(self, question: str, context_chunks: List[Dict]) -> str:
        """Simple keyword-based answer extraction (fallback)"""
        question_lower = question.lower()
        keywords = set(question_lower.split())
        
        # Find most relevant sentence from context
        best_sentence = ""
        best_score = 0
        
        for chunk in context_chunks:
            sentences = chunk["text"].split(". ")
            for sentence in sentences:
                sentence_lower = sentence.lower()
                score = sum(1 for keyword in keywords if keyword in sentence_lower)
                if score > best_score:
                    best_score = score
                    best_sentence = sentence
        
        return best_sentence if best_sentence else "I cannot find this information in the document."
    
    def _calculate_confidence(
        self,
        similarity_scores: List[float],
        context_chunks: List[Dict],
        answer: str
    ) -> float:
        """
        Calculate confidence score based on:
        - Retrieval similarity scores
        - Answer coverage of context
        - Chunk agreement
        """
        if not similarity_scores:
            return 0.0
        
        # Base confidence from average similarity
        avg_similarity = np.mean(similarity_scores)
        
        # Boost if multiple chunks agree (high similarity across chunks)
        similarity_std = np.std(similarity_scores)
        agreement_boost = 1.0 - min(similarity_std, 0.3)  # Lower std = higher agreement
        
        # Check if answer contains key terms from question
        answer_lower = answer.lower()
        question_terms = set()
        for chunk in context_chunks[:2]:  # Check top 2 chunks
            words = chunk["text"].lower().split()
            question_terms.update(words[:10])  # Top words
        
        coverage = sum(1 for term in question_terms if term in answer_lower) / max(len(question_terms), 1)
        coverage_boost = min(coverage * 0.2, 0.2)
        
        # Penalize if answer indicates missing information
        if any(phrase in answer_lower for phrase in ["cannot find", "not in", "not available", "not found"]):
            penalty = 0.5
        else:
            penalty = 1.0
        
        # Combine factors
        confidence = (avg_similarity * 0.6 + agreement_boost * 0.2 + coverage_boost) * penalty
        return min(max(confidence, 0.0), 1.0)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between vectors"""
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1, axis=1, keepdims=True) + 1e-8)
        vec2_norm = vec2 / (np.linalg.norm(vec2, axis=1, keepdims=True) + 1e-8)
        
        # Calculate cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm.T)
        return similarity
    
    def get_document_text(self, document_id: str) -> str:
        """Get full document text"""
        if document_id not in self.vector_store:
            raise ValueError(f"Document {document_id} not found")
        return self.vector_store[document_id]["full_text"]
