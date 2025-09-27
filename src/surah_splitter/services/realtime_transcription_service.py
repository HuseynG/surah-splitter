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
from surah_splitter.services.quran_word_tracker import QuranWordTracker
from surah_splitter.utils.app_logger import logger
from surah_splitter.utils.audio_processing import AudioProcessor


class RealtimeTranscriptionService:
    """
    Real-time transcription service that provides live feedback on Quran recitation.
    """

    def __init__(self):
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.transcription_service = HybridTranscriptionService()
        self.word_tracker = QuranWordTracker()
        self.reference_text = ""
        self.reference_words = []
        self.current_word_index = 0
        self.word_feedback_callback = None
        self.audio_buffer = deque(maxlen=100)  # Keep last 5 seconds at 20fps
        self.sample_rate = 16000
        self.chunk_duration = 0.5  # 500ms chunks for better speech detection
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.min_audio_length = 1.0  # Minimum 1 second of audio before processing
        self.current_surah = None
        self.audio_processor = AudioProcessor(sample_rate=self.sample_rate)
        self.enable_audio_processing = True
        
    def initialize(
        self,
        reference_surah_text: str,
        surah_number: int = 1,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        word_feedback_callback: Optional[Callable] = None,
        preloaded_service=None,
        latency_mode: str = "balanced"
    ):
        """
        Initialize the real-time service.

        Args:
            reference_surah_text: The correct Quran text to compare against
            azure_endpoint: Azure OpenAI endpoint
            api_key: Azure OpenAI API key
            word_feedback_callback: Callback function for word-level feedback
            preloaded_service: Pre-initialized transcription service (optional)
            latency_mode: Feedback latency mode ('instant', 'balanced', 'accurate')
        """
        logger.info(f"Initializing real-time transcription service in {latency_mode} mode")

        # Configure based on latency mode
        if latency_mode == "instant":
            self.chunk_duration = 0.2  # 200ms chunks for fastest feedback
            self.min_audio_length = 0.5  # Process after 0.5s
        elif latency_mode == "accurate":
            self.chunk_duration = 1.0  # 1s chunks for best accuracy
            self.min_audio_length = 2.0  # Process after 2s
        else:  # balanced
            self.chunk_duration = 0.5  # 500ms chunks
            self.min_audio_length = 1.0  # Process after 1s

        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.latency_mode = latency_mode
        
        # Use preloaded service if available, otherwise initialize new one
        if preloaded_service:
            logger.info("✅ Using preloaded transcription models")
            self.transcription_service = preloaded_service
        else:
            logger.info("⏳ Initializing transcription models on-demand...")
            self.transcription_service.initialize(
                azure_endpoint=azure_endpoint,
                api_key=api_key
            )
        
        # Set reference text and parse words
        self.reference_text = reference_surah_text
        self.reference_words = self._parse_arabic_words(reference_surah_text)
        self.word_feedback_callback = word_feedback_callback
        self.current_surah = surah_number
        
        # Initialize word tracker with surah context
        self.word_tracker.set_current_context(surah_number)
        
        logger.info(f"Loaded reference text with {len(self.reference_words)} words for Surah {surah_number}")

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
                
                # Process every 2 seconds or when we have enough audio
                current_time = time.time()
                if (current_time - last_transcription_time >= 2.0 and 
                    len(accumulated_audio) > 0):
                    
                    # Combine audio chunks
                    audio_data = np.concatenate(accumulated_audio)
                    
                    # Only process if we have enough audio
                    if len(audio_data) / self.sample_rate >= self.min_audio_length:
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
        """Save audio data to temporary WAV file with optional processing."""
        import soundfile as sf

        # Apply audio processing if enabled
        if self.enable_audio_processing:
            processed_audio, info = self.audio_processor.process_audio(
                audio_data,
                enable_noise_reduction=True,
                enable_vad=True,
                enable_agc=True,
                enable_highpass=True
            )

            # Log audio stats
            if info['has_speech']:
                logger.debug(f"🎤 Audio processed: gain={info['gain_applied']:.2f}, has_speech={info['has_speech']}")
            else:
                logger.warning("🔇 No speech detected in audio after VAD")

            audio_data = processed_audio

        temp_path = Path("/tmp/realtime_audio.wav")
        sf.write(temp_path, audio_data, self.sample_rate)
        return temp_path

    def _process_transcription(self, audio_path: Path):
        """Process transcription and provide word-level feedback."""
        try:
            # Get transcription with word timing
            result = self.transcription_service.transcribe_and_align(audio_path)
            transcribed_words = result.get("word_segments", [])
            transcribed_text = result.get("transcription", {}).get("text", "")
            
            # Log what the user said
            if transcribed_text:
                logger.info(f"🎤 USER SAID: '{transcribed_text}'")
                logger.info(f"📝 WORDS DETECTED: {len(transcribed_words)} words")
                for i, word in enumerate(transcribed_words):
                    logger.info(f"   Word {i+1}: '{word.get('word', '')}' ({word.get('start', 0):.2f}s - {word.get('end', 0):.2f}s)")
            else:
                logger.warning("🔇 No speech detected in audio chunk")
            
            # Compare with reference and provide feedback
            feedback = self._compare_with_reference(transcribed_words)
            
            # Log feedback details
            if feedback.get("word_feedback"):
                logger.info(f"📊 FEEDBACK: {len(feedback['word_feedback'])} word matches, accuracy: {feedback.get('overall_accuracy', 0)*100:.1f}%")
            
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

            # Add pronunciation hint if score is low
            if match_result["score"] < 0.6:
                hint = self._get_pronunciation_hint(
                    transcribed_word,
                    match_result["reference_word"]
                )
                if hint:
                    word_feedback["hint"] = hint
            
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
        Find the best matching word in reference text using intelligent tracking.
        
        Args:
            transcribed_word: The word that was transcribed
            start_position: Current position in reference text
            
        Returns:
            Match result with score and position
        """
        best_score = 0.0
        best_position = start_position
        best_reference_word = ""
        
        # Use word tracker's current position as starting point
        tracker_position = self.word_tracker.current_position
        search_start = max(start_position, tracker_position)
        
        # Search in a window from current tracker position forward
        search_window = 10  # Increased window for better matching
        start_idx = search_start
        end_idx = min(len(self.reference_words), search_start + search_window)
        
        for i in range(start_idx, end_idx):
            reference_word = self.reference_words[i]
            
            # Check if we can match at this position
            if not self.word_tracker.can_match_word_at_position(reference_word, i):
                continue
            
            # Use word tracker's intelligent scoring with context
            score = self.word_tracker.get_word_match_score(
                transcribed_word, reference_word, i, self.reference_words
            )
            
            if score > best_score:
                best_score = score
                best_position = i
                best_reference_word = reference_word
        
        # If we found a good match, confirm it with the tracker
        if best_score > 0.7:  # High confidence threshold
            self.word_tracker.confirm_word_match(best_reference_word, best_position)
            logger.info(f"🎯 Confirmed match: '{transcribed_word}' → '{best_reference_word}' at position {best_position}")
        
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

    def _get_pronunciation_hint(self, transcribed: str, reference: str) -> Optional[str]:
        """
        Generate pronunciation hints for mismatched words.

        Args:
            transcribed: What was heard
            reference: What was expected

        Returns:
            Pronunciation hint string or None
        """
        hints = []

        # Clean words for comparison
        clean_transcribed = self._clean_arabic_word(transcribed)
        clean_reference = self._clean_arabic_word(reference)

        # Check for common pronunciation mistakes
        if len(clean_reference) > len(clean_transcribed):
            hints.append(f"Try to pronounce all letters: {reference}")
        elif len(clean_reference) < len(clean_transcribed):
            hints.append(f"Word should be shorter: {reference}")

        # Check for specific letter differences
        if 'ص' in reference and 'س' in transcribed:
            hints.append("Use emphatic 'Saad' (ص) not 'Seen' (س)")
        elif 'ض' in reference and 'د' in transcribed:
            hints.append("Use emphatic 'Daad' (ض) not 'Dal' (د)")
        elif 'ط' in reference and 'ت' in transcribed:
            hints.append("Use emphatic 'Taa' (ط) not 'Ta' (ت)")
        elif 'ظ' in reference and 'ذ' in transcribed:
            hints.append("Use emphatic 'Dhaa' (ظ) not 'Thal' (ذ)")
        elif 'ق' in reference and 'ك' in transcribed:
            hints.append("Use deep 'Qaaf' (ق) from throat, not 'Kaaf' (ك)")
        elif 'غ' in reference and 'ع' in transcribed:
            hints.append("Use 'Ghayn' (غ) not 'Ayn' (ع)")
        elif 'ح' in reference and 'ه' in transcribed:
            hints.append("Use 'Haa' (ح) from throat, not soft 'Ha' (ه)")

        # Return the most relevant hint
        return hints[0] if hints else None

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
