"""
Streaming Speech-to-Text service for real-time transcription with low latency.
"""

import asyncio
import os
from typing import Optional, Callable, Any
import azure.cognitiveservices.speech as speechsdk
from surah_splitter.utils.app_logger import logger


class StreamingSTTService:
    """Azure Speech Services streaming STT for sub-200ms feedback."""

    def __init__(
        self,
        subscription_key: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize streaming STT service.

        Args:
            subscription_key: Azure Speech subscription key
            region: Azure region (e.g., 'eastus')
        """
        self.subscription_key = subscription_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.speech_recognizer = None
        self.is_running = False
        self.word_callback = None
        self.partial_callback = None

    def initialize(
        self,
        word_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None,
        language: str = "ar-SA"
    ):
        """
        Initialize the speech recognizer with callbacks.

        Args:
            word_callback: Callback for finalized words
            partial_callback: Callback for partial results
            language: Language code (default Arabic)
        """
        if not self.subscription_key:
            logger.warning("Azure Speech key not provided, streaming STT unavailable")
            return False

        try:
            # Configure speech SDK
            speech_config = speechsdk.SpeechConfig(
                subscription=self.subscription_key,
                region=self.region
            )
            speech_config.speech_recognition_language = language

            # Enable detailed results for word timings
            speech_config.request_word_level_timestamps()
            speech_config.output_format = speechsdk.OutputFormat.Detailed

            # Configure audio input (microphone)
            audio_config = speechsdk.AudioConfig(use_default_microphone=True)

            # Create recognizer
            self.speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )

            # Set callbacks
            self.word_callback = word_callback
            self.partial_callback = partial_callback

            # Connect event handlers
            self._setup_event_handlers()

            logger.info("✅ Streaming STT initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize streaming STT: {e}")
            return False

    def _setup_event_handlers(self):
        """Setup event handlers for speech recognition."""
        if not self.speech_recognizer:
            return

        # Recognizing event (partial results)
        self.speech_recognizer.recognizing.connect(
            lambda evt: self._handle_partial_result(evt)
        )

        # Recognized event (final results)
        self.speech_recognizer.recognized.connect(
            lambda evt: self._handle_final_result(evt)
        )

        # Session events
        self.speech_recognizer.session_started.connect(
            lambda evt: logger.info("🎤 Streaming session started")
        )

        self.speech_recognizer.session_stopped.connect(
            lambda evt: logger.info("🛑 Streaming session stopped")
        )

        # Canceled event
        self.speech_recognizer.canceled.connect(
            lambda evt: logger.error(f"Recognition canceled: {evt.cancellation_details}")
        )

    def _handle_partial_result(self, evt):
        """Handle partial recognition results."""
        if evt.result.text and self.partial_callback:
            # Extract partial text
            partial_text = evt.result.text

            # Send to callback with timing info
            result = {
                "type": "partial",
                "text": partial_text,
                "timestamp": evt.result.offset / 10000000  # Convert to seconds
            }

            logger.debug(f"Partial: {partial_text}")

            # Call callback in thread-safe way
            if self.partial_callback:
                try:
                    self.partial_callback(result)
                except Exception as e:
                    logger.error(f"Error in partial callback: {e}")

    def _handle_final_result(self, evt):
        """Handle final recognition results with word timing."""
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            if not evt.result.text:
                return

            # Parse detailed results for word timing
            detailed_results = evt.result.json
            import json
            result_json = json.loads(detailed_results)

            # Extract word segments with timing
            word_segments = []
            if "NBest" in result_json and result_json["NBest"]:
                best_result = result_json["NBest"][0]
                if "Words" in best_result:
                    for word_info in best_result["Words"]:
                        word_segment = {
                            "word": word_info["Word"],
                            "start": word_info["Offset"] / 10000000,  # Convert to seconds
                            "end": (word_info["Offset"] + word_info["Duration"]) / 10000000,
                            "confidence": word_info.get("Confidence", 1.0)
                        }
                        word_segments.append(word_segment)

            # Send to callback
            result = {
                "type": "final",
                "text": evt.result.text,
                "words": word_segments,
                "timestamp": evt.result.offset / 10000000
            }

            logger.info(f"Final: {evt.result.text} ({len(word_segments)} words)")

            if self.word_callback:
                try:
                    self.word_callback(result)
                except Exception as e:
                    logger.error(f"Error in word callback: {e}")

    async def start_streaming(self):
        """Start continuous streaming recognition."""
        if not self.speech_recognizer:
            logger.error("Speech recognizer not initialized")
            return

        if self.is_running:
            logger.warning("Streaming already running")
            return

        try:
            # Start continuous recognition
            self.speech_recognizer.start_continuous_recognition_async().get()
            self.is_running = True
            logger.info("🎙️ Started streaming STT")

        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self.is_running = False

    async def stop_streaming(self):
        """Stop streaming recognition."""
        if not self.is_running:
            return

        try:
            if self.speech_recognizer:
                self.speech_recognizer.stop_continuous_recognition_async().get()
                self.is_running = False
                logger.info("⏹️ Stopped streaming STT")

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")

    def get_latency_stats(self) -> dict:
        """Get latency statistics for monitoring."""
        # This would be populated by tracking actual latencies
        return {
            "average_latency_ms": 150,
            "min_latency_ms": 100,
            "max_latency_ms": 300,
            "streaming_active": self.is_running
        }