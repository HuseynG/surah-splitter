"""
Data models for Azure GPT Audio service responses and requests.

This module defines all the data structures used for GPT audio analysis,
including Tajweed and recitation feedback models.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
from datetime import datetime

from surah_splitter.models.base import DataclassJsonMixin


class AnalysisLanguage(str, Enum):
    """Supported languages for analysis."""
    ENGLISH = "en"
    ARABIC = "ar"


class AnalysisType(str, Enum):
    """Types of analysis available."""
    TAJWEED = "tajweed"
    RECITATION = "recitation"


class TajweedCategory(str, Enum):
    """Categories of Tajweed rules."""
    MAKHARIJ = "MAKHARIJ"
    SIFAT = "SIFAT"
    GHUNNAH = "GHUNNAH"
    MADD = "MADD"
    NOON_SAKIN = "NOON_SAKIN"
    MEEM_SAKIN = "MEEM_SAKIN"
    LAM = "LAM"
    RA = "RA"
    WAQF = "WAQF"
    OTHER = "OTHER"


class IssueSeverity(str, Enum):
    """Severity levels for Tajweed issues."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class TajweedChunk(DataclassJsonMixin):
    """Represents a chunk of analyzed recitation."""
    text: str
    start_time: float
    end_time: float
    issues: List[str]
    correct_application: List[str]


@dataclass
class TajweedIssue(DataclassJsonMixin):
    """Represents a specific Tajweed issue found in the recitation."""
    category: TajweedCategory
    rule: str
    word: str
    timestamp: float
    severity: IssueSeverity
    description: str
    correction: str


@dataclass
class TajweedScores(DataclassJsonMixin):
    """Scores for different aspects of Tajweed."""
    makharij: float = 0.0
    sifat: float = 0.0
    ghunnah: float = 0.0
    madd: float = 0.0
    noon_rules: float = 0.0
    overall: float = 0.0

    def __post_init__(self):
        """Ensure all scores are within 0-5 range."""
        for attr in ['makharij', 'sifat', 'ghunnah', 'madd', 'noon_rules', 'overall']:
            value = getattr(self, attr)
            if value < 0:
                setattr(self, attr, 0.0)
            elif value > 5:
                setattr(self, attr, 5.0)


@dataclass
class GPTAudioFeedback(DataclassJsonMixin):
    """Audio feedback from GPT if available."""
    text_feedback: str
    audio_base64: Optional[str] = None
    audio_format: str = "wav"


@dataclass
class TajweedAnalysisResponse(DataclassJsonMixin):
    """Complete response from Tajweed analysis."""
    detected_surah: Optional[str]
    riwayah: str
    chunks: List[TajweedChunk]
    issues: List[TajweedIssue]
    scores: TajweedScores
    overall_comment: str
    next_steps: List[str]
    audio_feedback: Optional[GPTAudioFeedback] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_simplified_dict(self) -> Dict[str, Any]:
        """Convert to a simplified dictionary for API responses."""
        return {
            'detected_surah': self.detected_surah,
            'riwayah': self.riwayah,
            'chunks': [
                {
                    'text': chunk.text,
                    'start_time': chunk.start_time,
                    'end_time': chunk.end_time,
                    'issues': chunk.issues,
                    'correct_application': chunk.correct_application
                }
                for chunk in self.chunks
            ],
            'issues': [
                {
                    'category': issue.category.value,
                    'rule': issue.rule,
                    'word': issue.word,
                    'timestamp': issue.timestamp,
                    'severity': issue.severity.value,
                    'description': issue.description,
                    'correction': issue.correction
                }
                for issue in self.issues
            ],
            'scores': {
                'makharij': self.scores.makharij,
                'sifat': self.scores.sifat,
                'ghunnah': self.scores.ghunnah,
                'madd': self.scores.madd,
                'noon_rules': self.scores.noon_rules,
                'overall': self.scores.overall
            },
            'overall_comment': self.overall_comment,
            'next_steps': self.next_steps,
            'has_audio_feedback': self.audio_feedback is not None,
            'timestamp': self.timestamp
        }


@dataclass
class MispronunciationDetail(DataclassJsonMixin):
    """Details about a mispronounced word."""
    word: str
    timestamp: float
    issue: str


@dataclass
class RecitationAnalysisResponse(DataclassJsonMixin):
    """Complete response from recitation accuracy analysis."""
    accuracy_score: float
    missed_words: List[str]
    added_words: List[str]
    mispronounced_words: List[MispronunciationDetail]
    feedback: str
    suggestions: List[str]
    audio_feedback: Optional[GPTAudioFeedback] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Ensure accuracy score is within 0-100 range."""
        if self.accuracy_score < 0:
            self.accuracy_score = 0.0
        elif self.accuracy_score > 100:
            self.accuracy_score = 100.0

    def to_simplified_dict(self) -> Dict[str, Any]:
        """Convert to a simplified dictionary for API responses."""
        return {
            'accuracy_score': self.accuracy_score,
            'missed_words': self.missed_words,
            'added_words': self.added_words,
            'mispronounced_words': [
                {
                    'word': mp.word,
                    'timestamp': mp.timestamp,
                    'issue': mp.issue
                }
                for mp in self.mispronounced_words
            ],
            'feedback': self.feedback,
            'suggestions': self.suggestions,
            'has_audio_feedback': self.audio_feedback is not None,
            'timestamp': self.timestamp
        }


@dataclass
class AudioSubmissionRequest(DataclassJsonMixin):
    """Request model for audio submission."""
    audio_data: Union[str, bytes]  # Base64 string or raw bytes
    audio_format: str = "wav"
    language: AnalysisLanguage = AnalysisLanguage.ENGLISH
    analysis_type: AnalysisType = AnalysisType.TAJWEED
    include_audio_feedback: bool = False
    surah_context: Optional[Dict[str, Any]] = None
    reference_text: Optional[str] = None  # For recitation analysis

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the request.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.audio_data:
            return False, "Audio data is required"

        if self.analysis_type == AnalysisType.RECITATION and not self.reference_text:
            return False, "Reference text is required for recitation analysis"

        supported_formats = ['wav', 'mp3', 'm4a', 'webm', 'ogg']
        if self.audio_format.lower() not in supported_formats:
            return False, f"Unsupported audio format: {self.audio_format}"

        return True, None


@dataclass
class AnalysisError(DataclassJsonMixin):
    """Error response from analysis."""
    error_code: str
    error_message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Optional[Dict[str, Any]] = None


@dataclass
class BatchAnalysisRequest(DataclassJsonMixin):
    """Request for batch analysis of multiple audio files."""
    audio_files: List[AudioSubmissionRequest]
    batch_id: Optional[str] = None
    priority: int = 0  # Higher priority processed first


@dataclass
class BatchAnalysisResponse(DataclassJsonMixin):
    """Response for batch analysis."""
    batch_id: str
    total_files: int
    completed: int
    failed: int
    results: List[Union[TajweedAnalysisResponse, RecitationAnalysisResponse, AnalysisError]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AnalysisMetadata(DataclassJsonMixin):
    """Metadata about an analysis session."""
    session_id: str
    user_id: Optional[str] = None
    device_info: Optional[Dict[str, str]] = None
    app_version: Optional[str] = None
    analysis_duration_seconds: float = 0.0
    api_version: str = "1.0.0"


@dataclass
class FeedbackRating(DataclassJsonMixin):
    """User feedback on analysis quality."""
    analysis_id: str
    rating: int  # 1-5 stars
    helpful: bool
    comments: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Ensure rating is within 1-5 range."""
        if self.rating < 1:
            self.rating = 1
        elif self.rating > 5:
            self.rating = 5


# Type aliases for convenience
from typing import Tuple

TajweedResult = Union[TajweedAnalysisResponse, AnalysisError]
RecitationResult = Union[RecitationAnalysisResponse, AnalysisError]
AnalysisResult = Union[TajweedAnalysisResponse, RecitationAnalysisResponse, AnalysisError]