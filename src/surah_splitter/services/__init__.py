"""
Service module initialization.

This module provides various services for Quran recitation analysis,
including transcription, Tajweed analysis, and GPT-powered audio feedback.
"""

# Core services
from surah_splitter.services.transcription_service import TranscriptionService
from surah_splitter.services.ayah_matching_service import AyahMatchingService
from surah_splitter.services.segmentation_service import SegmentationService
from surah_splitter.services.quran_metadata_service import QuranMetadataService
from surah_splitter.services.pipeline_service import PipelineService

# Azure services
from surah_splitter.services.azure_transcription_service import AzureTranscriptionService

# GPT Audio services (new)
from surah_splitter.services.azure_gpt_audio_service import AzureGPTAudioService
from surah_splitter.services.prompt_templates import PromptBuilder

# Analysis services
from surah_splitter.services.tajweed_analyzer import TajweedAnalyzer
from surah_splitter.services.hybrid_transcription_service import HybridTranscriptionService
from surah_splitter.services.realtime_transcription_service import RealtimeTranscriptionService
from surah_splitter.services.personalized_learning import PersonalizedLearningService
from surah_splitter.services.progress_tracker import ProgressTracker

__all__ = [
    # Core services
    'TranscriptionService',
    'AyahMatchingService',
    'SegmentationService',
    'QuranMetadataService',
    'PipelineService',

    # Azure services
    'AzureTranscriptionService',

    # GPT Audio services
    'AzureGPTAudioService',
    'PromptBuilder',

    # Analysis services
    'TajweedAnalyzer',
    'HybridTranscriptionService',
    'RealtimeTranscriptionService',
    'PersonalizedLearningService',
    'ProgressTracker',
]
