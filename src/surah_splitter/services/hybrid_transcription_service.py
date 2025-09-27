"""
Hybrid transcription service that combines Azure OpenAI for quality with local models for word timing.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import re
from dotenv import load_dotenv

from surah_splitter.services.azure_transcription_service import AzureTranscriptionService
from surah_splitter.services.transcription_service import TranscriptionService
from surah_splitter.models.all_models import RecognizedSentencesAndWords
from surah_splitter.utils.app_logger import logger

# Load environment variables
load_dotenv()


class HybridTranscriptionService:
    """
    Hybrid service that uses Azure for high-quality transcription and local models for word timing.
    """

    def __init__(self):
        self.azure_service = AzureTranscriptionService()
        self.local_service = TranscriptionService()

    def initialize(
        self,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment_name: Optional[str] = None,
        local_model_name: str = "OdyAsh/faster-whisper-base-ar-quran",
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        """
        Initialize both Azure and local transcription services.
        
        Args:
            azure_endpoint: Azure OpenAI endpoint
            api_key: Azure OpenAI API key
            api_version: Azure API version
            deployment_name: Azure deployment name
            local_model_name: Local model for word timing
            device: Device for local model (cpu/cuda)
            compute_type: Compute type for local model
        """
        logger.info("Initializing hybrid transcription service")
        
        # Initialize Azure service for high-quality transcription
        self.azure_service.initialize(azure_endpoint, api_key, api_version, deployment_name)
        
        # Initialize local service for word-level timing
        self.local_service.initialize(local_model_name, device, compute_type)

    def transcribe_and_align(self, audio_path: Path, output_dir: Optional[Path] = None) -> RecognizedSentencesAndWords:
        """
        Transcribe using Azure for quality, then align words using local model for timing.
        
        Args:
            audio_path: Path to audio file
            output_dir: Optional output directory
            
        Returns:
            Combined result with Azure transcription quality and local word timing
        """
        logger.info(f"Starting hybrid transcription of: {audio_path}")
        
        # Step 1: Get high-quality transcription from Azure
        logger.info("Step 1: Getting high-quality transcription from Azure OpenAI")
        azure_result = self.azure_service.transcribe_and_align(audio_path, output_dir)
        azure_text = azure_result["transcription"]["text"]
        
        # Step 2: Get word-level timing from local model
        logger.info("Step 2: Getting word-level timing from local model")
        local_result = self.local_service.transcribe_and_align(audio_path, output_dir)
        local_word_segments = local_result.get("word_segments", [])
        
        # Step 3: Align Azure text with local word timing
        logger.info("Step 3: Aligning Azure text with local word timing")
        aligned_word_segments = self._align_texts_with_timing(
            azure_text, 
            local_word_segments
        )
        
        # Step 4: Create final result
        result = {
            "transcription": {
                "segments": [{
                    "start": aligned_word_segments[0]["start"] if aligned_word_segments else 0.0,
                    "end": aligned_word_segments[-1]["end"] if aligned_word_segments else 0.0,
                    "text": azure_text
                }],
                "text": azure_text,
                "language": "ar"
            },
            "word_segments": aligned_word_segments
        }
        
        logger.success(f"Hybrid transcription complete: {len(aligned_word_segments)} word segments")
        return result

    def _align_texts_with_timing(self, azure_text: str, local_word_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Align high-quality Azure text with local model word timing.
        
        Args:
            azure_text: High-quality transcription from Azure
            local_word_segments: Word segments with timing from local model
            
        Returns:
            Word segments with Azure text quality and local timing
        """
        # Clean and tokenize both texts
        azure_words = self._tokenize_arabic(azure_text)
        local_words = [self._clean_arabic_word(seg["word"]) for seg in local_word_segments]
        
        logger.debug(f"Azure words: {len(azure_words)}, Local words: {len(local_words)}")
        
        # Simple alignment: match words by similarity
        aligned_segments = []
        local_idx = 0
        
        for azure_word in azure_words:
            if local_idx >= len(local_word_segments):
                # No more local segments, use estimated timing
                estimated_start = aligned_segments[-1]["end"] if aligned_segments else 0.0
                estimated_end = estimated_start + 0.5  # 500ms default
                
                aligned_segments.append({
                    "word": azure_word,
                    "start": estimated_start,
                    "end": estimated_end,
                    "score": 0.5  # Lower confidence for estimated timing
                })
                continue
            
            # Find best matching local word
            best_match_idx = self._find_best_word_match(azure_word, local_words[local_idx:], local_idx)
            
            if best_match_idx is not None:
                local_seg = local_word_segments[best_match_idx]
                aligned_segments.append({
                    "word": azure_word,  # Use Azure's high-quality text
                    "start": local_seg["start"],
                    "end": local_seg["end"],
                    "score": local_seg.get("score", 1.0)
                })
                local_idx = best_match_idx + 1
            else:
                # No good match found, estimate timing
                if aligned_segments:
                    estimated_start = aligned_segments[-1]["end"]
                    estimated_end = estimated_start + 0.5
                else:
                    estimated_start = 0.0
                    estimated_end = 0.5
                
                aligned_segments.append({
                    "word": azure_word,
                    "start": estimated_start,
                    "end": estimated_end,
                    "score": 0.3  # Low confidence for estimated timing
                })
        
        return aligned_segments

    def _tokenize_arabic(self, text: str) -> List[str]:
        """Tokenize Arabic text into words."""
        # Remove diacritics and clean text
        cleaned = self._clean_arabic_word(text)
        # Split by whitespace and filter empty strings
        words = [word.strip() for word in cleaned.split() if word.strip()]
        return words

    def _clean_arabic_word(self, word: str) -> str:
        """Clean Arabic word by removing diacritics and non-Arabic characters."""
        # Keep only Arabic letters and spaces
        word = re.sub(r"[^\u060f\u0620-\u064a\u066e\u066f\u0671-\u06d3\u06d5\s]", "", word)
        # Normalize spaces
        word = re.sub(r"\s+", " ", word).strip()
        return word

    def _find_best_word_match(self, azure_word: str, local_words: List[str], start_idx: int) -> Optional[int]:
        """
        Find the best matching local word for the Azure word.
        
        Args:
            azure_word: Word from Azure transcription
            local_words: List of local words to search
            start_idx: Starting index in the original local_words list
            
        Returns:
            Index of best match in original local_words list, or None
        """
        azure_clean = self._clean_arabic_word(azure_word)
        
        # Look for exact match first (within next 3 words)
        for i, local_word in enumerate(local_words[:3]):
            if azure_clean == local_word:
                return start_idx + i
        
        # Look for partial match (within next 5 words)
        for i, local_word in enumerate(local_words[:5]):
            if len(azure_clean) >= 3 and len(local_word) >= 3:
                if azure_clean in local_word or local_word in azure_clean:
                    return start_idx + i
        
        # No good match found
        return None
