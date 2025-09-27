"""
Real-time transcription service for live Quran recitation feedback.
"""

import asyncio
import json
import queue
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
import numpy as np
import sounddevice as sd
from collections import deque

from surah_splitter.services.hybrid_transcription_service import HybridTranscriptionService
from surah_splitter.utils.app_logger import logger


class RealtimeTranscriptionService:
    """
    Real-time transcription service that provides live feedback on Quran recitation.
    """

    def __init__(self):
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.transcription_service = HybridTranscriptionService()
        self.reference_text = ""
        self.reference_words = []
        self.current_word_index = 0
        self.word_feedback_callback = None
        self.audio_buffer = deque(maxlen=100)  # Keep last 5 seconds at 20fps
        self.sample_rate = 16000
        self.chunk_duration = 0.5  # 500ms chunks for better speech detection
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.min_audio_length = 1.0  # Minimum 1 second of audio before processing
        
    def initialize(
        self,
        reference_surah_text: str,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        word_feedback_callback: Optional[Callable] = None
    ):
        """
        
        Args:
            reference_surah_text: The correct Quran text to compare against
            azure_endpoint: Azure OpenAI endpoint
            api_key: Azure OpenAI API key
            word_feedback_callback: Callback function to send feedback to connected clients
    """Callback function to send feedback to connected clients."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.send_feedback(feedback))
        else:
            loop.run_until_complete(manager.send_feedback(feedback))
    except RuntimeError:
        # No event loop running, create a new one
        asyncio.run(manager.send_feedback(feedback))
        )
        
        # Set reference text and parse words
        self.reference_text = reference_surah_text
        self.reference_words = self._parse_arabic_words(reference_surah_text)
        self.word_feedback_callback = word_feedback_callback
        
        logger.info(f"Loaded reference text with {len(self.reference_words)} words")

    def start_listening(self):
        """Start real-time audio capture and transcription."""
        logger.info("Starting real-time listening...")
        self.is_recording = True
        self.current_word_index = 0
        
        # Start audio capture thread
        audio_thread = threading.Thread(target=self._audio_capture_loop)
        audio_thread.daemon = True
        audio_thread.start()
        
        # Start transcription processing thread
        transcription_thread = threading.Thread(target=self._transcription_loop)
        transcription_thread.daemon = True
        transcription_thread.start()

    def stop_listening(self):
        """Stop real-time audio capture and transcription."""
        logger.info("Stopping real-time listening...")
        self.is_recording = False

    def _audio_capture_loop(self):
        """Continuously capture audio in small chunks."""
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            # Add audio chunk to queue
            audio_chunk = indata[:, 0].copy()  # Take first channel
            self.audio_queue.put(audio_chunk)
            
            # Also add to rolling buffer
            self.audio_buffer.append(audio_chunk)

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype=np.float32
            ):
                while self.is_recording:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Audio capture error: {e}")

    def _transcription_loop(self):
        """Process audio chunks and provide real-time feedback."""
        accumulated_audio = []
        last_transcription_time = time.time()
        
        while self.is_recording:
            try:
                # Get audio chunk (with timeout)
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    accumulated_audio.append(chunk)
                except queue.Empty:
                    continue
                
                # Process every 1 second or when we have enough audio
                current_time = time.time()
                if (current_time - last_transcription_time >= 1.0 and 
                    len(accumulated_audio) > 0):
                    
                    # Combine audio chunks
                    audio_data = np.concatenate(accumulated_audio)
                    
                    # Save to temporary file and transcribe
                    temp_audio_path = self._save_temp_audio(audio_data)
                    
                    # Get transcription (async to avoid blocking)
                    threading.Thread(
                        target=self._process_transcription,
                        args=(temp_audio_path,)
                    ).start()
                    
                    # Reset for next batch
                    accumulated_audio = []
                    last_transcription_time = current_time
                    
            except Exception as e:
                logger.error(f"Transcription loop error: {e}")

    def _save_temp_audio(self, audio_data: np.ndarray) -> Path:
        """Save audio data to temporary WAV file."""
        import soundfile as sf
        
        temp_path = Path("/tmp/realtime_audio.wav")
        sf.write(temp_path, audio_data, self.sample_rate)
        return temp_path

    def _process_transcription(self, audio_path: Path):
        """Process transcription and provide word-level feedback."""
        try:
            # Get transcription with word timing
            result = self.transcription_service.transcribe_and_align(audio_path)
            transcribed_words = result.get("word_segments", [])
            
            # Compare with reference and provide feedback
            feedback = self._compare_with_reference(transcribed_words)
            
            # Send feedback via callback
            if self.word_feedback_callback:
                self.word_feedback_callback(feedback)
                
        except Exception as e:
            logger.error(f"Transcription processing error: {e}")

    def _compare_with_reference(self, transcribed_words: List[Dict]) -> Dict[str, Any]:
        """
        Compare transcribed words with reference text and generate feedback.
        
        Args:
            transcribed_words: List of transcribed word segments
            
        Returns:
            Feedback dictionary with word-level alignment scores
        """
        feedback = {
            "timestamp": time.time(),
            "word_feedback": [],
            "overall_accuracy": 0.0,
            "current_position": self.current_word_index
        }
        
        for word_seg in transcribed_words:
            transcribed_word = self._clean_arabic_word(word_seg["word"])
            
            # Find best match in reference text
            match_result = self._find_word_match(
                transcribed_word, 
                self.current_word_index
            )
            
            word_feedback = {
                "transcribed_word": transcribed_word,
                "reference_word": match_result["reference_word"],
                "alignment_score": match_result["score"],
                "color": self._get_feedback_color(match_result["score"]),
                "position": match_result["position"],
                "timing": {
                    "start": word_seg["start"],
                    "end": word_seg["end"]
                }
            }
            
            feedback["word_feedback"].append(word_feedback)
            
            # Update current position if good match
            if match_result["score"] > 0.7:
                self.current_word_index = match_result["position"] + 1
        
        # Calculate overall accuracy
        if feedback["word_feedback"]:
            scores = [w["alignment_score"] for w in feedback["word_feedback"]]
            feedback["overall_accuracy"] = sum(scores) / len(scores)
        
        return feedback

    def _find_word_match(self, transcribed_word: str, start_position: int) -> Dict[str, Any]:
        """
        Find the best matching word in reference text.
        
        Args:
            transcribed_word: The word that was transcribed
            start_position: Current position in reference text
            
        Returns:
            Match result with score and position
        """
        best_score = 0.0
        best_position = start_position
        best_reference_word = ""
        
        # Search in a window around current position
        search_window = 5
        start_idx = max(0, start_position - search_window)
        end_idx = min(len(self.reference_words), start_position + search_window)
        
        for i in range(start_idx, end_idx):
            reference_word = self.reference_words[i]
            score = self._calculate_word_similarity(transcribed_word, reference_word)
            
            if score > best_score:
                best_score = score
                best_position = i
                best_reference_word = reference_word
        
        return {
            "score": best_score,
            "position": best_position,
            "reference_word": best_reference_word
        }

    def _calculate_word_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two Arabic words."""
        # Clean both words
        clean1 = self._clean_arabic_word(word1)
        clean2 = self._clean_arabic_word(word2)
        
        # Exact match
        if clean1 == clean2:
            return 1.0
        
        # Partial match (for different pronunciations)
        if len(clean1) >= 3 and len(clean2) >= 3:
            if clean1 in clean2 or clean2 in clean1:
                return 0.8
        
        # Character-level similarity (simple Levenshtein-like)
        max_len = max(len(clean1), len(clean2))
        if max_len == 0:
            return 0.0
        
        common_chars = sum(1 for c1, c2 in zip(clean1, clean2) if c1 == c2)
        return common_chars / max_len

    def _clean_arabic_word(self, word: str) -> str:
        """Clean Arabic word by removing diacritics."""
        import re
        # Remove diacritics and keep only Arabic letters
        cleaned = re.sub(r"[^\u0621-\u063A\u0641-\u064A]", "", word)
        return cleaned.strip()

    def _parse_arabic_words(self, text: str) -> List[str]:
        """Parse Arabic text into individual words."""
        # Split by whitespace first, then clean each word
        raw_words = text.split()
        words = []
        for word in raw_words:
            cleaned = self._clean_arabic_word(word)
            if cleaned:  # Only add non-empty words
                words.append(cleaned)
        return words

    def _get_feedback_color(self, score: float) -> str:
        """Get color code based on alignment score."""
        if score >= 0.9:
            return "green"      # Perfect match
        elif score >= 0.7:
            return "yellow"     # Good match
        elif score >= 0.4:
            return "orange"     # Partial match
        else:
            return "red"        # Poor/no match

    def get_current_progress(self) -> Dict[str, Any]:
        """Get current progress through the reference text."""
        total_words = len(self.reference_words)
        progress_percentage = (self.current_word_index / total_words) * 100 if total_words > 0 else 0
        
        return {
            "current_word_index": self.current_word_index,
            "total_words": total_words,
            "progress_percentage": progress_percentage,
            "current_word": self.reference_words[self.current_word_index] if self.current_word_index < total_words else "",
            "remaining_words": total_words - self.current_word_index
        }
