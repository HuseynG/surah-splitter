"""
Tests for Azure GPT Audio Service.

This module provides comprehensive tests for the Azure GPT Audio service,
including Tajweed and recitation analysis functionality.
"""

import pytest
import asyncio
import json
import base64
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from surah_splitter.services.azure_gpt_audio_service import AzureGPTAudioService
from surah_splitter.models.gpt_audio_models import (
    TajweedAnalysisResponse,
    RecitationAnalysisResponse,
    TajweedChunk,
    TajweedIssue,
    TajweedScores,
    TajweedCategory,
    IssueSeverity,
    MispronunciationDetail,
    GPTAudioFeedback,
    AnalysisLanguage
)
from surah_splitter.utils.config_manager import GPTAudioConfig


@pytest.fixture
def mock_config():
    """Create a mock GPT Audio configuration."""
    config = Mock(spec=GPTAudioConfig)
    config.api_key = "test-api-key"
    config.endpoint = "https://test.openai.azure.com"
    config.deployment_name = "gpt-audio-test"
    config.api_version = "2024-10-01-preview"
    config.is_valid.return_value = True
    return config


@pytest.fixture
def mock_openai_client():
    """Create a mock Azure OpenAI client."""
    client = Mock()
    return client


@pytest.fixture
def gpt_audio_service(mock_config, mock_openai_client):
    """Create a GPT Audio service instance with mocks."""
    service = AzureGPTAudioService()

    # Mock the configuration and client
    with patch.object(service, 'config', mock_config):
        with patch.object(service, 'client', mock_openai_client):
            service.is_initialized = True
            yield service


@pytest.fixture
def sample_audio_bytes():
    """Generate sample audio bytes for testing."""
    # Create a minimal WAV header + some data
    wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    audio_data = b'\x00\x01' * 1000  # Some sample audio data
    return wav_header + audio_data


@pytest.fixture
def mock_tajweed_response():
    """Create a mock Tajweed analysis API response."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = json.dumps({
        "detected_surah": "Al-Fatiha",
        "riwayah": "Hafs",
        "chunks": [
            {
                "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                "start_time": 0.0,
                "end_time": 3.5,
                "issues": ["Minor Ghunnah issue"],
                "correct_application": ["Proper Madd application"]
            }
        ],
        "issues": [
            {
                "category": "GHUNNAH",
                "rule": "Ghunnah duration",
                "word": "الرَّحْمَٰنِ",
                "timestamp": 2.1,
                "severity": "LOW",
                "description": "Ghunnah slightly short",
                "correction": "Extend Ghunnah to 2 counts"
            }
        ],
        "scores": {
            "makharij": 92.5,
            "sifat": 88.0,
            "ghunnah": 85.0,
            "madd": 95.0,
            "noon_rules": 90.0,
            "overall": 90.1
        },
        "overall_comment": "Good recitation with minor areas for improvement",
        "next_steps": [
            "Practice Ghunnah duration",
            "Review Noon Sakinah rules"
        ]
    })
    return response


@pytest.fixture
def mock_recitation_response():
    """Create a mock recitation analysis API response."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = json.dumps({
        "accuracy_score": 87.5,
        "missed_words": ["الْعَالَمِينَ"],
        "added_words": [],
        "mispronounced_words": [
            {
                "word": "الرَّحِيمِ",
                "timestamp": 3.2,
                "issue": "Incorrect vowel length"
            }
        ],
        "feedback": "Good effort with some pronunciation improvements needed",
        "suggestions": [
            "Practice the pronunciation of 'الرَّحِيمِ'",
            "Review the complete verse to avoid omissions"
        ]
    })
    return response


class TestAzureGPTAudioService:
    """Test cases for Azure GPT Audio Service."""

    def test_initialization(self):
        """Test service initialization."""
        service = AzureGPTAudioService()
        assert service.client is None
        assert service.config is None
        assert service.prompt_builder is not None
        assert not service.is_initialized

    @patch('surah_splitter.services.azure_gpt_audio_service.GPTAudioConfig')
    @patch('surah_splitter.services.azure_gpt_audio_service.AzureOpenAI')
    def test_initialize(self, mock_azure_openai, mock_config_class):
        """Test service initialization with configuration."""
        # Setup mocks
        mock_config = Mock()
        mock_config.is_valid.return_value = True
        mock_config.api_key = "test-key"
        mock_config.api_version = "2024-10-01"
        mock_config.endpoint = "https://test.azure.com"
        mock_config_class.return_value = mock_config

        service = AzureGPTAudioService()
        service.initialize()

        assert service.is_initialized
        assert service.config is not None
        mock_azure_openai.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_tajweed(self, gpt_audio_service, sample_audio_bytes, mock_tajweed_response):
        """Test Tajweed analysis functionality."""
        # Mock the API call
        gpt_audio_service.client.chat.completions.create.return_value = mock_tajweed_response

        # Mock audio encoding
        with patch('surah_splitter.services.azure_gpt_audio_service.encode_audio_for_gpt') as mock_encode:
            mock_encode.return_value = (
                base64.b64encode(sample_audio_bytes).decode('utf-8'),
                {"format": "wav", "duration": 3.5}
            )

            # Perform analysis
            result = await gpt_audio_service.analyze_tajweed(
                audio_input=sample_audio_bytes,
                language="en",
                surah_context={"surah": "Al-Fatiha", "ayah": 1}
            )

        # Assertions
        assert isinstance(result, TajweedAnalysisResponse)
        assert result.detected_surah == "Al-Fatiha"
        assert result.riwayah == "Hafs"
        assert len(result.chunks) == 1
        assert isinstance(result.chunks[0], TajweedChunk)
        assert result.chunks[0].text == "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
        assert len(result.issues) == 1
        assert isinstance(result.issues[0], TajweedIssue)
        assert result.issues[0].category == TajweedCategory.GHUNNAH
        assert isinstance(result.scores, TajweedScores)
        assert result.scores.overall == 90.1

    @pytest.mark.asyncio
    async def test_analyze_recitation(self, gpt_audio_service, sample_audio_bytes, mock_recitation_response):
        """Test recitation analysis functionality."""
        # Mock the API call
        gpt_audio_service.client.chat.completions.create.return_value = mock_recitation_response

        # Mock audio encoding
        with patch('surah_splitter.services.azure_gpt_audio_service.encode_audio_for_gpt') as mock_encode:
            mock_encode.return_value = (
                base64.b64encode(sample_audio_bytes).decode('utf-8'),
                {"format": "wav", "duration": 4.0}
            )

            # Perform analysis
            result = await gpt_audio_service.analyze_recitation(
                audio_input=sample_audio_bytes,
                reference_text="بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                language="en"
            )

        # Assertions
        assert isinstance(result, RecitationAnalysisResponse)
        assert result.accuracy_score == 87.5
        assert result.missed_words == ["الْعَالَمِينَ"]
        assert len(result.mispronounced_words) == 1
        assert isinstance(result.mispronounced_words[0], MispronunciationDetail)
        assert result.mispronounced_words[0].word == "الرَّحِيمِ"
        assert result.feedback == "Good effort with some pronunciation improvements needed"

    @pytest.mark.asyncio
    async def test_analyze_tajweed_with_audio_feedback(self, gpt_audio_service, sample_audio_bytes):
        """Test Tajweed analysis with audio feedback."""
        # Create response with audio
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = json.dumps({
            "detected_surah": "Al-Baqarah",
            "riwayah": "Warsh",
            "chunks": [],
            "issues": [],
            "scores": {
                "makharij": 95.0,
                "sifat": 95.0,
                "ghunnah": 95.0,
                "madd": 95.0,
                "noon_rules": 95.0,
                "overall": 95.0
            },
            "overall_comment": "Excellent recitation",
            "next_steps": []
        })

        # Add audio data
        response.choices[0].message.audio = {
            "data": base64.b64encode(b"audio_feedback_data").decode('utf-8'),
            "format": "wav"
        }

        gpt_audio_service.client.chat.completions.create.return_value = response

        with patch('surah_splitter.services.azure_gpt_audio_service.encode_audio_for_gpt') as mock_encode:
            mock_encode.return_value = ("base64_audio", {"format": "wav"})

            result = await gpt_audio_service.analyze_tajweed(
                audio_input=sample_audio_bytes,
                include_audio_feedback=True
            )

        assert result.audio_feedback is not None
        assert isinstance(result.audio_feedback, GPTAudioFeedback)
        assert result.audio_feedback.audio_format == "wav"

    def test_validate_audio_input_valid_file(self, gpt_audio_service, tmp_path):
        """Test audio validation with valid file."""
        # Create a test file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)

        is_valid, error = gpt_audio_service.validate_audio_input(str(audio_file))
        assert is_valid
        assert error is None

    def test_validate_audio_input_missing_file(self, gpt_audio_service):
        """Test audio validation with missing file."""
        is_valid, error = gpt_audio_service.validate_audio_input("/nonexistent/file.wav")
        assert not is_valid
        assert "not found" in error

    def test_validate_audio_input_large_file(self, gpt_audio_service, tmp_path):
        """Test audio validation with file exceeding size limit."""
        # Create a large file (>25MB)
        large_file = tmp_path / "large.wav"
        large_file.write_bytes(b"\x00" * (26 * 1024 * 1024))

        is_valid, error = gpt_audio_service.validate_audio_input(str(large_file))
        assert not is_valid
        assert "too large" in error

    def test_validate_audio_input_bytes(self, gpt_audio_service):
        """Test audio validation with bytes input."""
        audio_bytes = b"RIFF" + b"\x00" * 1000
        is_valid, error = gpt_audio_service.validate_audio_input(audio_bytes)
        assert is_valid
        assert error is None

    @pytest.mark.asyncio
    async def test_get_supported_languages(self, gpt_audio_service):
        """Test getting supported languages."""
        languages = await gpt_audio_service.get_supported_languages()
        assert "en" in languages
        assert "ar" in languages

    @pytest.mark.asyncio
    async def test_test_connection_success(self, gpt_audio_service):
        """Test connection testing - success case."""
        # Mock successful response
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Hello"
        gpt_audio_service.client.chat.completions.create.return_value = response

        result = await gpt_audio_service.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, gpt_audio_service):
        """Test connection testing - failure case."""
        # Mock failed response
        gpt_audio_service.client.chat.completions.create.side_effect = Exception("Connection failed")

        result = await gpt_audio_service.test_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_parse_tajweed_response_with_invalid_enums(self, gpt_audio_service):
        """Test parsing Tajweed response with invalid enum values (fallback to defaults)."""
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = json.dumps({
            "detected_surah": "Test Surah",
            "riwayah": "Hafs",
            "chunks": [],
            "issues": [
                {
                    "category": "INVALID_CATEGORY",  # Invalid category
                    "rule": "Test rule",
                    "word": "test",
                    "timestamp": 1.0,
                    "severity": "INVALID_SEVERITY",  # Invalid severity
                    "description": "Test",
                    "correction": "Test correction"
                }
            ],
            "scores": {
                "makharij": 80,
                "sifat": 80,
                "ghunnah": 80,
                "madd": 80,
                "noon_rules": 80,
                "overall": 80
            },
            "overall_comment": "Test",
            "next_steps": []
        })

        result = gpt_audio_service._parse_tajweed_response(response, False)

        # Should fallback to OTHER and MEDIUM
        assert result.issues[0].category == TajweedCategory.OTHER
        assert result.issues[0].severity == IssueSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_parse_recitation_response_string_format(self, gpt_audio_service):
        """Test parsing recitation response with string-only mispronunciations."""
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = json.dumps({
            "accuracy_score": 75.0,
            "missed_words": [],
            "added_words": [],
            "mispronounced_words": ["word1", "word2"],  # Simple strings
            "feedback": "Test feedback",
            "suggestions": []
        })

        result = gpt_audio_service._parse_recitation_response(response, False)

        assert len(result.mispronounced_words) == 2
        assert result.mispronounced_words[0].word == "word1"
        assert result.mispronounced_words[0].timestamp == 0.0
        assert result.mispronounced_words[1].word == "word2"

    @pytest.mark.asyncio
    async def test_error_handling_in_analyze_tajweed(self, gpt_audio_service, sample_audio_bytes):
        """Test error handling in Tajweed analysis."""
        # Mock API error
        gpt_audio_service.client.chat.completions.create.side_effect = Exception("API Error")

        with patch('surah_splitter.services.azure_gpt_audio_service.encode_audio_for_gpt') as mock_encode:
            mock_encode.return_value = ("base64_audio", {"format": "wav"})

            with pytest.raises(Exception) as exc_info:
                await gpt_audio_service.analyze_tajweed(sample_audio_bytes)

            assert "API Error" in str(exc_info.value)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for Azure GPT Audio Service."""

    @pytest.mark.skipif(not Path(".env").exists(), reason="No .env file found")
    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Test real connection to Azure service (requires valid .env)."""
        service = AzureGPTAudioService()
        service.initialize()

        result = await service.test_connection()
        assert isinstance(result, bool)