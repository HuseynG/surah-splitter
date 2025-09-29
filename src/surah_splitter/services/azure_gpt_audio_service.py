"""
Azure GPT Audio Service for Tajweed and Recitation Analysis.

This service integrates with Azure OpenAI's GPT audio models to provide
comprehensive Tajweed and Quranic recitation analysis.
"""

import os
import json
import base64
from typing import Optional, Dict, Any, Union, Tuple
from pathlib import Path
import asyncio
from datetime import datetime

from openai import AzureOpenAI
from dotenv import load_dotenv

from loguru import logger
from surah_splitter.utils.audio_encoding import encode_audio_for_gpt, decode_gpt_audio_response
from surah_splitter.services.prompt_templates import PromptBuilder
from surah_splitter.models.gpt_audio_models import (
    TajweedAnalysisResponse,
    RecitationAnalysisResponse,
    GPTAudioFeedback,
    AnalysisLanguage,
    AnalysisType,
    TajweedChunk,
    TajweedIssue,
    TajweedScores,
    TajweedCategory,
    IssueSeverity,
    MispronunciationDetail
)
from surah_splitter.utils.config_manager import GPTAudioConfig

# Load environment variables
load_dotenv()


class AzureGPTAudioService:
    """Service for analyzing Quranic recitation using Azure GPT Audio models."""

    def __init__(self):
        """Initialize the Azure GPT Audio Service."""
        self.client: Optional[AzureOpenAI] = None
        self.config: Optional[GPTAudioConfig] = None
        self.prompt_builder = PromptBuilder()
        self.is_initialized = False

        logger.info("AzureGPTAudioService instance created")

    def initialize(self) -> None:
        """Initialize the service with Azure OpenAI client and configuration."""
        if self.is_initialized:
            logger.debug("AzureGPTAudioService already initialized")
            return

        try:
            # Load configuration
            self.config = GPTAudioConfig()
            self.config.load_from_env()

            # Validate configuration
            if not self.config.is_valid():
                raise ValueError("Invalid GPT Audio configuration. Check environment variables.")

            # Initialize Azure OpenAI client
            self.client = AzureOpenAI(
                api_key=self.config.api_key,
                api_version=self.config.api_version,
                azure_endpoint=self.config.endpoint,
                default_headers={
                    "Content-Type": "application/json",
                    "User-Agent": "SurahSplitter/1.0"
                }
            )

            self.is_initialized = True
            logger.info("AzureGPTAudioService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AzureGPTAudioService: {str(e)}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized before use."""
        if not self.is_initialized:
            self.initialize()

    async def analyze_tajweed(
        self,
        audio_input: Union[str, bytes, Path],
        language: str = "en",
        surah_context: Optional[Dict[str, Any]] = None,
        include_audio_feedback: bool = False
    ) -> TajweedAnalysisResponse:
        """
        Analyze Tajweed rules in the provided audio recitation.

        Args:
            audio_input: Audio file path, bytes, or Path object
            language: Language for feedback ('en' or 'ar')
            surah_context: Optional context about the Surah/Ayah being recited
            include_audio_feedback: Whether to request audio feedback from GPT

        Returns:
            TajweedAnalysisResponse with detailed analysis
        """
        self._ensure_initialized()

        try:
            logger.info("Starting Tajweed analysis")
            # Encode audio for API submission
            audio_base64, audio_metadata = encode_audio_for_gpt(audio_input)

            # Get appropriate prompts
            system_prompt, user_prompt = self.prompt_builder.get_tajweed_prompt(
                language=AnalysisLanguage(language),
                audio_context=surah_context
            )

            # Prepare messages for GPT
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": audio_metadata.get("format", "wav")
                            }
                        }
                    ]
                }
            ]

            # Add audio output configuration if requested
            audio_config = {}
            if include_audio_feedback:
                audio_config = {
                    "modalities": ["text", "audio"],
                    "audio": {
                        "voice": "alloy",
                        "format": "wav"
                    }
                }

            logger.debug(f"Sending Tajweed analysis request for {audio_metadata.get('duration', 0):.2f}s audio")

            # Add JSON instruction to ensure JSON response
            if messages and len(messages) > 1:
                # The content is an array, so append a new text object
                messages[-1]["content"].append({
                    "type": "text",
                    "text": "\n\nIMPORTANT: Respond ONLY with valid JSON format, no additional text."
                })

            # Call GPT Audio API (without response_format as it's not supported)
            response = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=2000,
                **audio_config
            )

            # Parse response
            result = self._parse_tajweed_response(response, include_audio_feedback)

            logger.info(f"Tajweed analysis completed successfully for language: {language}")
            return result

        except Exception as e:
            logger.error(f"Tajweed analysis failed: {str(e)}")
            raise

    async def analyze_recitation(
        self,
        audio_input: Union[str, bytes, Path],
        reference_text: str,
        language: str = "en",
        surah_info: Optional[Dict[str, Any]] = None,
        include_audio_feedback: bool = False
    ) -> RecitationAnalysisResponse:
        """
        Analyze recitation accuracy against reference text.

        Args:
            audio_input: Audio file path, bytes, or Path object
            reference_text: The correct Arabic text to compare against
            language: Language for feedback ('en' or 'ar')
            surah_info: Optional information about the Surah/Ayah
            include_audio_feedback: Whether to request audio feedback

        Returns:
            RecitationAnalysisResponse with accuracy analysis
        """
        self._ensure_initialized()

        try:
            logger.info("Starting recitation analysis")
            # Encode audio
            audio_base64, audio_metadata = encode_audio_for_gpt(audio_input)

            # Get recitation prompts
            system_prompt, user_prompt = self.prompt_builder.get_recitation_prompt(
                language=AnalysisLanguage(language),
                reference_text=reference_text,
                audio_context=surah_info
            )

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": audio_metadata.get("format", "wav")
                            }
                        }
                    ]
                }
            ]

            # Audio configuration
            audio_config = {}
            if include_audio_feedback:
                audio_config = {
                    "modalities": ["text", "audio"],
                    "audio": {
                        "voice": "alloy",
                        "format": "wav"
                    }
                }

            logger.debug(f"Sending recitation analysis request")

            # Add JSON instruction to ensure JSON response
            if messages and len(messages) > 1:
                # The content is an array, so append a new text object
                messages[-1]["content"].append({
                    "type": "text",
                    "text": "\n\nIMPORTANT: Respond ONLY with valid JSON format, no additional text."
                })

            # Call API (without response_format as it's not supported)
            response = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=messages,
                temperature=0.2,  # Even lower for accuracy checking
                max_tokens=1500,
                **audio_config
            )

            # Parse response
            result = self._parse_recitation_response(response, include_audio_feedback)

            logger.info("Recitation analysis completed successfully")
            return result

        except Exception as e:
            logger.error(f"Recitation analysis failed: {str(e)}")
            raise

    def _parse_tajweed_response(
        self,
        response: Any,
        include_audio: bool
    ) -> TajweedAnalysisResponse:
        """Parse the GPT response into a TajweedAnalysisResponse."""
        try:
            # Extract text content
            text_content = response.choices[0].message.content

            # Parse JSON response
            if isinstance(text_content, str):
                analysis_data = json.loads(text_content)
            else:
                analysis_data = text_content

            # Parse chunks into TajweedChunk instances
            chunks = []
            for chunk_data in analysis_data.get('chunks', []):
                chunk = TajweedChunk(
                    text=chunk_data.get('text', ''),
                    start_time=float(chunk_data.get('start_time', 0.0)),
                    end_time=float(chunk_data.get('end_time', 0.0)),
                    issues=chunk_data.get('issues', []),
                    correct_application=chunk_data.get('correct_application', [])
                )
                chunks.append(chunk)

            # Parse issues into TajweedIssue instances
            issues = []
            for issue_data in analysis_data.get('issues', []):
                # Parse category enum with fallback
                try:
                    category = TajweedCategory(issue_data.get('category', 'OTHER'))
                except ValueError:
                    category = TajweedCategory.OTHER

                # Parse severity enum with fallback
                try:
                    severity = IssueSeverity(issue_data.get('severity', 'MEDIUM'))
                except ValueError:
                    severity = IssueSeverity.MEDIUM

                issue = TajweedIssue(
                    category=category,
                    rule=issue_data.get('rule', ''),
                    word=issue_data.get('word', ''),
                    timestamp=float(issue_data.get('timestamp', 0.0)),
                    severity=severity,
                    description=issue_data.get('description', ''),
                    correction=issue_data.get('correction', '')
                )
                issues.append(issue)

            # Parse scores into TajweedScores instance
            scores_data = analysis_data.get('scores', {})
            scores = TajweedScores(
                makharij=float(scores_data.get('makharij', 0.0)),
                sifat=float(scores_data.get('sifat', 0.0)),
                ghunnah=float(scores_data.get('ghunnah', 0.0)),
                madd=float(scores_data.get('madd', 0.0)),
                noon_rules=float(scores_data.get('noon_rules', 0.0)),
                overall=float(scores_data.get('overall', 0.0))
            )

            # Extract audio if present
            audio_feedback = None
            if include_audio and hasattr(response.choices[0].message, 'audio'):
                audio_data = response.choices[0].message.audio
                if audio_data:
                    audio_feedback = GPTAudioFeedback(
                        text_feedback=analysis_data.get('overall_comment', ''),
                        audio_base64=audio_data.get('data'),
                        audio_format=audio_data.get('format', 'wav')
                    )

            # Create response object with proper dataclass instances
            tajweed_response = TajweedAnalysisResponse(
                detected_surah=analysis_data.get('detected_surah'),
                riwayah=analysis_data.get('riwayah', 'Hafs'),
                chunks=chunks,
                issues=issues,
                scores=scores,
                overall_comment=analysis_data.get('overall_comment', ''),
                next_steps=analysis_data.get('next_steps', []),
                audio_feedback=audio_feedback,
                timestamp=datetime.now().isoformat()
            )

            return tajweed_response

        except Exception as e:
            logger.error(f"Failed to parse Tajweed response: {str(e)}")
            raise

    def _parse_recitation_response(
        self,
        response: Any,
        include_audio: bool
    ) -> RecitationAnalysisResponse:
        """Parse the GPT response into a RecitationAnalysisResponse."""
        try:
            # Extract text content
            text_content = response.choices[0].message.content

            # Parse JSON
            if isinstance(text_content, str):
                analysis_data = json.loads(text_content)
            else:
                analysis_data = text_content

            # Parse mispronounced words into MispronunciationDetail instances
            mispronounced_words = []
            mispronounced_data = analysis_data.get('mispronounced_words', [])

            # Handle both list of dicts and list of strings formats
            for item in mispronounced_data:
                if isinstance(item, dict):
                    # If it's already a dict with word, timestamp, issue
                    detail = MispronunciationDetail(
                        word=item.get('word', ''),
                        timestamp=float(item.get('timestamp', 0.0)),
                        issue=item.get('issue', '')
                    )
                elif isinstance(item, str):
                    # If it's just a string, create detail with defaults
                    detail = MispronunciationDetail(
                        word=item,
                        timestamp=0.0,
                        issue='Pronunciation issue'
                    )
                else:
                    # Skip invalid items
                    logger.warning(f"Skipping invalid mispronunciation item: {item}")
                    continue

                mispronounced_words.append(detail)

            # Extract audio if present
            audio_feedback = None
            if include_audio and hasattr(response.choices[0].message, 'audio'):
                audio_data = response.choices[0].message.audio
                if audio_data:
                    audio_feedback = GPTAudioFeedback(
                        text_feedback=analysis_data.get('feedback', ''),
                        audio_base64=audio_data.get('data'),
                        audio_format=audio_data.get('format', 'wav')
                    )

            # Create response with proper dataclass instances
            recitation_response = RecitationAnalysisResponse(
                accuracy_score=float(analysis_data.get('accuracy_score', 0.0)),
                missed_words=analysis_data.get('missed_words', []),
                added_words=analysis_data.get('added_words', []),
                mispronounced_words=mispronounced_words,
                feedback=analysis_data.get('feedback', ''),
                suggestions=analysis_data.get('suggestions', []),
                audio_feedback=audio_feedback,
                timestamp=datetime.now().isoformat()
            )

            return recitation_response

        except Exception as e:
            logger.error(f"Failed to parse recitation response: {str(e)}")
            raise

    def validate_audio_input(
        self,
        audio_input: Union[str, bytes, Path]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate the audio input before processing.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if isinstance(audio_input, (str, Path)):
                path = Path(audio_input) if isinstance(audio_input, str) else audio_input
                if not path.exists():
                    return False, f"Audio file not found: {path}"

                # Check file size (max 25MB for GPT audio)
                file_size_mb = path.stat().st_size / (1024 * 1024)
                if file_size_mb > 25:
                    return False, f"Audio file too large: {file_size_mb:.2f}MB (max 25MB)"

            elif isinstance(audio_input, bytes):
                # Check bytes size
                size_mb = len(audio_input) / (1024 * 1024)
                if size_mb > 25:
                    return False, f"Audio data too large: {size_mb:.2f}MB (max 25MB)"
            else:
                return False, f"Unsupported audio input type: {type(audio_input)}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def get_supported_languages(self) -> list[str]:
        """Get list of supported languages for analysis."""
        return [lang.value for lang in AnalysisLanguage]

    async def test_connection(self) -> bool:
        """Test the connection to Azure GPT Audio service."""
        self._ensure_initialized()

        try:
            # Send a simple test message
            response = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10
            )

            return response.choices[0].message.content is not None

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False