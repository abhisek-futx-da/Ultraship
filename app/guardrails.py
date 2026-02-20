"""
Guardrails Module
Implements safety checks to prevent hallucinations and ensure grounded answers
"""

from typing import List, Dict


class Guardrails:
    """Guardrails to prevent hallucinations and ensure answer quality"""
    
    def __init__(self):
        self.min_similarity_threshold = 0.3  # Minimum similarity score to allow answer
        self.min_chunks_required = 1  # Minimum number of relevant chunks
    
    def check(
        self,
        question: str,
        chunks: List[Dict],
        similarity_scores: List[float]
    ) -> Dict:
        """
        Check if answer should be allowed based on guardrails
        
        Returns:
            Dict with 'allowed', 'message', and 'reason' keys
        """
        # Guardrail 1: Check if we have any relevant chunks
        if not chunks or len(chunks) == 0:
            return {
                "allowed": False,
                "message": "I cannot find relevant information in the document to answer this question.",
                "reason": "no_relevant_chunks"
            }
        
        # Guardrail 2: Check similarity threshold
        if similarity_scores:
            max_similarity = max(similarity_scores)
            if max_similarity < self.min_similarity_threshold:
                return {
                    "allowed": False,
                    "message": f"I cannot find this information in the document. The retrieved content has low relevance (similarity: {max_similarity:.2f}).",
                    "reason": "low_similarity",
                    "similarity_score": max_similarity
                }
        
        # Guardrail 3: Check if we have minimum required chunks
        if len(chunks) < self.min_chunks_required:
            return {
                "allowed": False,
                "message": "Insufficient context found in the document to provide a reliable answer.",
                "reason": "insufficient_chunks"
            }
        
        # Guardrail 4: Check if chunks are too short (likely noise)
        valid_chunks = [chunk for chunk in chunks if len(chunk.get("text", "").split()) >= 5]
        if len(valid_chunks) < self.min_chunks_required:
            return {
                "allowed": False,
                "message": "The retrieved document sections are too short to provide a meaningful answer.",
                "reason": "chunks_too_short"
            }
        
        # All guardrails passed
        return {
            "allowed": True,
            "message": "",
            "reason": "passed"
        }
    
    def validate_answer_grounding(
        self,
        answer: str,
        context_chunks: List[Dict]
    ) -> Dict:
        """
        Additional validation: Check if answer is grounded in context
        """
        answer_lower = answer.lower()
        
        # Check for phrases that indicate missing information
        missing_phrases = [
            "cannot find",
            "not in the document",
            "not available",
            "not found",
            "not mentioned"
        ]
        
        if any(phrase in answer_lower for phrase in missing_phrases):
            return {
                "grounded": False,
                "reason": "answer_indicates_missing_info"
            }
        
        # Check if answer contains words from context (simple grounding check)
        context_words = set()
        for chunk in context_chunks:
            words = chunk.get("text", "").lower().split()
            context_words.update(words[:50])  # Top 50 words from context
        
        answer_words = set(answer_lower.split())
        overlap = len(answer_words.intersection(context_words))
        overlap_ratio = overlap / max(len(answer_words), 1)
        
        if overlap_ratio < 0.1:  # Less than 10% word overlap
            return {
                "grounded": False,
                "reason": "low_word_overlap",
                "overlap_ratio": overlap_ratio
            }
        
        return {
            "grounded": True,
            "overlap_ratio": overlap_ratio
        }
