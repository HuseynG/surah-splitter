"""
Data models for Surah Splitter.

This module provides data models for various analysis types including
transcription, Tajweed analysis, and GPT-powered audio feedback.
"""

from surah_splitter.models.base import DataclassJsonMixin
from surah_splitter.models.all_models import (
    RecognizedSentencesAndWords,
    MatchedAyahsAndSpans,
    WordMatch,
    ReferenceWord,
    RecognizedWord,
    SegmentedWordSpan,
    SegmentationStats,
    AyahTimestamp,
)

# GPT Audio models (new)
from surah_splitter.models.gpt_audio_models import (
    AnalysisLanguage,
    AnalysisType,
    TajweedCategory,
    IssueSeverity,
    TajweedChunk,
    TajweedIssue,
    TajweedScores,
    GPTAudioFeedback,
    TajweedAnalysisResponse,
    MispronunciationDetail,
    RecitationAnalysisResponse,
    AudioSubmissionRequest,
    AnalysisError,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    AnalysisMetadata,
    FeedbackRating,
    TajweedResult,
    RecitationResult,
    AnalysisResult,
)

__all__ = [
    # Base classes
    "DataclassJsonMixin",

    # Core models
    "RecognizedSentencesAndWords",
    "MatchedAyahsAndSpans",
    "WordMatch",
    "ReferenceWord",
    "RecognizedWord",
    "SegmentedWordSpan",
    "SegmentationStats",
    "AyahTimestamp",

    # GPT Audio enums
    "AnalysisLanguage",
    "AnalysisType",
    "TajweedCategory",
    "IssueSeverity",

    # GPT Audio models
    "TajweedChunk",
    "TajweedIssue",
    "TajweedScores",
    "GPTAudioFeedback",
    "TajweedAnalysisResponse",
    "MispronunciationDetail",
    "RecitationAnalysisResponse",
    "AudioSubmissionRequest",
    "AnalysisError",
    "BatchAnalysisRequest",
    "BatchAnalysisResponse",
    "AnalysisMetadata",
    "FeedbackRating",

    # Type aliases
    "TajweedResult",
    "RecitationResult",
    "AnalysisResult",
]
