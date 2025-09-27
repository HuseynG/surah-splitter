"""
Azure OpenAI transcription service using Whisper API.
"""

import os
from pathlib import Path
from typing import Optional
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv

from surah_splitter.models.all_models import RecognizedSentencesAndWords
from surah_splitter.utils.app_logger import logger

# Load environment variables
load_dotenv()


class AzureTranscriptionService:
    """Service for transcribing audio using Azure OpenAI Whisper."""

    def __init__(self):
        self.client = None

    def initialize(
        self,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment_name: Optional[str] = None,
    ):
        """
        Initialize the Azure OpenAI client.

        Args:
            azure_endpoint: Your Azure OpenAI endpoint (defaults to env var)
            api_key: Your Azure OpenAI API key (defaults to env var)
            api_version: API version to use (defaults to env var)
            deployment_name: Name of your Whisper deployment (defaults to env var)
        """
        logger.info("Initializing Azure OpenAI transcription service")
        
        # Use environment variables as defaults
        azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
        api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")
        deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini-transcribe")
        
        if not azure_endpoint or not api_key:
            raise ValueError("Azure endpoint and API key must be provided either as parameters or environment variables")
        
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.deployment_name = deployment_name
        logger.info(f"Initialized with endpoint: {azure_endpoint}, deployment: {deployment_name}")

    def transcribe_and_align(self, audio_path: Path, output_dir: Optional[Path] = None) -> RecognizedSentencesAndWords:
        """
        Transcribe an audio file using Azure OpenAI Whisper.

        Args:
            audio_path: Path to the input audio file
            output_dir: Optional directory to save intermediate files

        Returns:
            A dictionary containing transcription results and word-level timestamps
        """
        logger.info(f"Transcribing audio file with Azure OpenAI: {audio_path}")

        if not self.client:
            raise ValueError("Azure OpenAI client not initialized. Call initialize() first.")

        # Open and transcribe the audio file
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model=self.deployment_name,
                file=audio_file,
                response_format="json",  # Use json format for gpt-4o-mini-transcribe
                language="ar",  # Arabic
            )

        # Convert Azure OpenAI format to our expected format
        # Note: gpt-4o-mini-transcribe doesn't provide word-level timestamps
        word_segments = []
        
        # Create segments for compatibility
        segments = [{
            "start": 0.0,
            "end": 0.0,  # No timing info available with this model
            "text": transcript.text
        }]

        result = {
            "transcription": {
                "segments": segments,
                "text": transcript.text,
                "language": "ar"
            },
            "word_segments": word_segments
        }

        logger.success(f"Azure transcription of {audio_path.name} complete")
        return result


class GPT4TranscriptionService:
    """Service for transcribing and analyzing audio using GPT-4o-mini."""

    def __init__(self):
        self.whisper_client = None
        self.gpt_client = None

    def initialize(
        self,
        azure_endpoint: str,
        api_key: str,
        api_version: str = "2024-02-01",
        whisper_deployment: str = "whisper-1",
        gpt_deployment: str = "gpt-4o-mini",
    ):
        """Initialize both Whisper and GPT-4o-mini clients."""
        logger.info("Initializing Azure OpenAI with Whisper + GPT-4o-mini")
        
        self.whisper_client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.gpt_client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.whisper_deployment = whisper_deployment
        self.gpt_deployment = gpt_deployment

    def transcribe_and_enhance(self, audio_path: Path, reference_text: Optional[str] = None) -> dict:
        """
        Transcribe audio with Whisper, then enhance/correct with GPT-4o-mini.

        Args:
            audio_path: Path to audio file
            reference_text: Optional reference Quran text for comparison

        Returns:
            Enhanced transcription with corrections and analysis
        """
        logger.info(f"Transcribing and enhancing: {audio_path}")

        # Step 1: Transcribe with Whisper
        with open(audio_path, "rb") as audio_file:
            transcript = self.whisper_client.audio.transcriptions.create(
                model=self.whisper_deployment,
                file=audio_file,
                response_format="text",
                language="ar"
            )

        # Step 2: Enhance with GPT-4o-mini
        enhancement_prompt = f"""
You are an expert in Quranic Arabic. Please analyze this transcribed Arabic text and:

1. Correct any obvious transcription errors
2. Add proper Arabic diacritics where missing
3. Identify which Surah and Ayahs this might be from
4. Rate the accuracy of the recitation (1-10)

Transcribed text: {transcript}

{f"Reference text: {reference_text}" if reference_text else ""}

Please respond in JSON format with:
{{
    "corrected_text": "corrected Arabic text",
    "identified_surah": "surah name/number",
    "identified_ayahs": ["ayah numbers"],
    "accuracy_score": "1-10 rating",
    "corrections_made": ["list of corrections"],
    "analysis": "detailed analysis"
}}
"""

        response = self.gpt_client.chat.completions.create(
            model=self.gpt_deployment,
            messages=[
                {"role": "system", "content": "You are an expert in Quranic Arabic and Islamic studies."},
                {"role": "user", "content": enhancement_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        import json
        enhanced_result = json.loads(response.choices[0].message.content)

        return {
            "original_transcription": transcript,
            "enhanced_analysis": enhanced_result,
            "word_segments": []  # Would need additional processing for word-level timing
        }
