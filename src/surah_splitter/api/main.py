"""
Comprehensive FastAPI application for Quran recitation feedback system.
All endpoints from the demo HTML are implemented here.
"""

import asyncio
import json
import io
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import numpy as np

from surah_splitter.services.realtime_transcription_service import RealtimeTranscriptionService
from surah_splitter.services.hybrid_transcription_service import HybridTranscriptionService
from surah_splitter.services.quran_metadata_service import QuranMetadataService
from surah_splitter.services.personalized_learning import PersonalizedLearningService
from surah_splitter.services.progress_tracker import ProgressTracker
from surah_splitter.services.azure_gpt_audio_service import AzureGPTAudioService
from surah_splitter.utils.app_logger import logger
from surah_splitter.utils.audio_encoding import (
    encode_audio_for_gpt,
    validate_audio_for_gpt,
    compress_audio_for_gpt
)
from surah_splitter.models.gpt_audio_models import (
    TajweedAnalysisResponse,
    RecitationAnalysisResponse,
    AudioSubmissionRequest,
    AnalysisLanguage,
    AnalysisType,
    AnalysisError
)

app = FastAPI(
    title="Quran Recitation Feedback API",
    description="""
    Comprehensive API for real-time Quran recitation feedback and learning.

    ## Features

    - **Real-time Transcription**: WebSocket-based real-time audio processing
    - **Tajweed Analysis**: Advanced AI-powered Tajweed rules evaluation using Azure GPT Audio
    - **Recitation Accuracy**: Compare recitation against reference text
    - **Personalized Learning**: Adaptive difficulty and progress tracking
    - **Multi-format Support**: Accepts audio files, base64 audio, and streaming

    ## GPT Audio Endpoints

    The API includes advanced GPT-powered audio analysis:

    - `/api/audio/analyze/tajweed`: Analyze Tajweed rules in recitation
    - `/api/audio/analyze/recitation`: Check recitation accuracy against reference

    Both endpoints support:
    - File uploads (multipart/form-data)
    - Base64 JSON submissions (application/json)
    - Multiple audio formats (WAV, MP3, M4A, WebM, OGG)
    - Multi-language feedback (English and Arabic)
    """,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "GPT Audio Analysis",
            "description": "Advanced AI-powered audio analysis using Azure GPT Audio models"
        },
        {
            "name": "Real-time",
            "description": "WebSocket-based real-time transcription and feedback"
        },
        {
            "name": "Session",
            "description": "Session management for recitation practice"
        },
        {
            "name": "Learning",
            "description": "Personalized learning and progress tracking"
        },
        {
            "name": "Metadata",
            "description": "Quran metadata and information"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class LatencyMode(str, Enum):
    INSTANT = "instant"
    BALANCED = "balanced"
    ACCURATE = "accurate"

class FeedbackColor(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"

class SessionStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

# Pydantic Models
class SurahInfo(BaseModel):
    number: int
    name: str
    english_name: str
    text: str
    total_ayahs: int
    revelation_type: str

class SessionConfig(BaseModel):
    surah_number: int
    latency_mode: LatencyMode = LatencyMode.BALANCED
    enable_tajweed: bool = True
    enable_hints: bool = True
    difficulty_level: int = Field(default=1, ge=1, le=5)

class WordFeedback(BaseModel):
    position: int
    reference_word: str
    transcribed_word: str
    confidence: float
    color: FeedbackColor
    hint: Optional[str] = None
    tajweed_issues: Optional[List[str]] = None

class SessionProgress(BaseModel):
    session_id: str
    surah_number: int
    current_position: int
    total_words: int
    progress_percentage: float
    accuracy: float
    duration: float
    status: SessionStatus

class AudioSubmission(BaseModel):
    audio_data: str  # Base64 encoded audio
    format: str = "webm"
    sample_rate: int = 16000

class ColorScheme(BaseModel):
    correct: str = "#4CAF50"
    partial: str = "#FFC107"
    incorrect: str = "#f44336"
    next_expected: str = "#2196F3"
    current: str = "#FFFF00"

class UISettings(BaseModel):
    color_scheme: ColorScheme
    font_size: int = 24
    show_hints: bool = True
    show_tajweed: bool = True
    animation_speed: float = 0.3

# GPT Audio Analysis Request/Response Models
class TajweedAnalysisRequest(BaseModel):
    """Request model for Tajweed analysis.

    Example:
    {
        "audio_data": "base64_encoded_audio_string...",
        "audio_format": "wav",
        "language": "en",
        "include_audio_feedback": false,
        "surah_context": {
            "surah_name": "Al-Fatiha",
            "surah_number": 1,
            "ayah_number": 1
        }
    }
    """
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    audio_format: str = Field("wav", description="Audio format (wav, mp3, m4a, webm, ogg)")
    language: str = Field("en", description="Language for feedback (en or ar)")
    include_audio_feedback: bool = Field(False, description="Include audio feedback in response")
    surah_context: Optional[Dict[str, Any]] = Field(None, description="Optional Surah/Ayah context")

class RecitationAnalysisRequest(BaseModel):
    """Request model for recitation accuracy analysis.

    Example:
    {
        "audio_data": "base64_encoded_audio_string...",
        "reference_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "audio_format": "wav",
        "language": "en",
        "include_audio_feedback": false,
        "surah_info": {
            "surah_name": "Al-Fatiha",
            "surah_number": 1,
            "ayah_number": 1
        }
    }
    """
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    reference_text: str = Field(..., description="The correct Arabic text to compare against")
    audio_format: str = Field("wav", description="Audio format (wav, mp3, m4a, webm, ogg)")
    language: str = Field("en", description="Language for feedback (en or ar)")
    include_audio_feedback: bool = Field(False, description="Include audio feedback in response")
    surah_info: Optional[Dict[str, Any]] = Field(None, description="Optional Surah/Ayah information")

class TajweedAnalysisAPIResponse(BaseModel):
    """API response wrapper for Tajweed analysis."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecitationAnalysisAPIResponse(BaseModel):
    """API response wrapper for recitation analysis."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Global service instances
realtime_service = RealtimeTranscriptionService()
hybrid_service = HybridTranscriptionService()
metadata_service = QuranMetadataService()
learning_service = PersonalizedLearningService()
progress_tracker = ProgressTracker()
gpt_audio_service = AzureGPTAudioService()

# Application start time for uptime tracking
app_start_time = datetime.now()

# Session management
active_sessions: Dict[str, Dict[str, Any]] = {}
feedback_queues: Dict[str, asyncio.Queue] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_to_session(self, session_id: str, data: Dict[str, Any]):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(data)
                except:
                    pass

    async def broadcast(self, data: Dict[str, Any]):
        for session_id in self.active_connections:
            await self.send_to_session(session_id, data)

manager = ConnectionManager()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services and preload models."""
    logger.info("🚀 Starting Quran Recitation API...")

    # Preload models
    asyncio.create_task(preload_models())

    # Start background processors
    asyncio.create_task(feedback_processor())

async def preload_models():
    """Preload AI models for faster response."""
    try:
        logger.info("📦 Preloading transcription models...")
        await asyncio.get_event_loop().run_in_executor(
            None, hybrid_service.initialize
        )
        logger.success("✅ Models preloaded successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to preload models: {e}")

async def feedback_processor():
    """Process feedback from queues and send to clients."""
    while True:
        for session_id, queue in list(feedback_queues.items()):
            try:
                if not queue.empty():
                    feedback = await asyncio.wait_for(queue.get(), timeout=0.1)
                    await manager.send_to_session(session_id, feedback)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing feedback: {e}")
        await asyncio.sleep(0.01)

# Surah Management Endpoints
@app.get("/api/surahs", response_model=List[SurahInfo])
async def get_all_surahs():
    """Get list of all available surahs."""
    # Hardcoded for demo - replace with actual metadata service
    surahs = [
        {
            "number": 1,
            "name": "الفاتحة",
            "english_name": "Al-Fatiha",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ الرَّحْمَٰنِ الرَّحِيمِ مَالِكِ يَوْمِ الدِّينِ إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ",
            "total_ayahs": 7,
            "revelation_type": "Meccan"
        },
        {
            "number": 112,
            "name": "الإخلاص",
            "english_name": "Al-Ikhlas",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",
            "total_ayahs": 4,
            "revelation_type": "Meccan"
        },
        {
            "number": 113,
            "name": "الفلق",
            "english_name": "Al-Falaq",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ مِن شَرِّ مَا خَلَقَ وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",
            "total_ayahs": 5,
            "revelation_type": "Meccan"
        },
        {
            "number": 114,
            "name": "الناس",
            "english_name": "An-Nas",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ قُلْ أَعُوذُ بِرَبِّ النَّاسِ مَلِكِ النَّاسِ إِلَٰهِ النَّاسِ مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ مِنَ الْجِنَّةِ وَالنَّاسِ",
            "total_ayahs": 6,
            "revelation_type": "Meccan"
        }
    ]

    return [
        SurahInfo(
            number=s["number"],
            name=s["name"],
            english_name=s["english_name"],
            text=s["text"],
            total_ayahs=s["total_ayahs"],
            revelation_type=s["revelation_type"]
        )
        for s in surahs
    ]

@app.get("/api/surahs/{surah_number}", response_model=SurahInfo)
async def get_surah(surah_number: int):
    """Get specific surah by number."""
    # Get from hardcoded list for now
    surahs_map = {
        1: {
            "number": 1,
            "name": "الفاتحة",
            "english_name": "Al-Fatiha",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ الرَّحْمَٰنِ الرَّحِيمِ مَالِكِ يَوْمِ الدِّينِ إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ",
            "total_ayahs": 7,
            "revelation_type": "Meccan"
        },
        112: {
            "number": 112,
            "name": "الإخلاص",
            "english_name": "Al-Ikhlas",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",
            "total_ayahs": 4,
            "revelation_type": "Meccan"
        }
    }

    surah = surahs_map.get(surah_number)
    if not surah:
        raise HTTPException(status_code=404, detail="Surah not found")

    return SurahInfo(
        number=surah["number"],
        name=surah["name"],
        english_name=surah["english_name"],
        text=surah["text"],
        total_ayahs=surah["total_ayahs"],
        revelation_type=surah["revelation_type"]
    )

@app.get("/api/surahs/search")
async def search_surahs(query: str = Query(..., description="Search query")):
    """Search surahs by name or number."""
    # Simple search implementation
    all_surahs = await get_all_surahs()
    query_lower = query.lower()

    results = []
    for surah in all_surahs:
        if (query_lower in surah.english_name.lower() or
            query_lower in surah.name or
            str(surah.number) == query):
            results.append(surah)

    return results

# Session Management Endpoints
@app.post("/api/sessions/start")
async def start_session(config: SessionConfig) -> Dict[str, Any]:
    """Start a new recitation session."""
    session_id = f"session_{datetime.now().timestamp()}"

    # Get surah text
    surah_response = await get_surah(config.surah_number)
    surah = surah_response.dict()

    # Initialize session
    active_sessions[session_id] = {
        "id": session_id,
        "config": config.dict(),
        "surah": surah,
        "status": SessionStatus.ACTIVE,
        "start_time": datetime.now().isoformat(),
        "current_position": 0,
        "accuracy": 0.0,
        "feedback_history": []
    }

    # Create feedback queue
    feedback_queues[session_id] = asyncio.Queue()

    # Initialize real-time service
    def feedback_callback(feedback: Dict[str, Any]):
        feedback_queues[session_id].put_nowait(feedback)

    realtime_service.initialize(
        reference_surah_text=surah["text"],
        surah_number=config.surah_number,
        word_feedback_callback=feedback_callback,
        latency_mode=config.latency_mode
    )

    # Don't start listening from microphone in Docker - audio comes via WebSocket
    # realtime_service.start_listening()

    return {
        "session_id": session_id,
        "surah": surah,
        "total_words": len(surah["text"].split()),
        "status": SessionStatus.ACTIVE
    }

@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop an active session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Don't stop listening since we're not using microphone
    # realtime_service.stop_listening()
    active_sessions[session_id]["status"] = SessionStatus.COMPLETED
    active_sessions[session_id]["end_time"] = datetime.now().isoformat()

    # Calculate final statistics
    session = active_sessions[session_id]

    return {
        "session_id": session_id,
        "status": SessionStatus.COMPLETED,
        "duration": (datetime.now() - datetime.fromisoformat(session["start_time"])).total_seconds(),
        "final_accuracy": session["accuracy"],
        "words_completed": session["current_position"]
    }

@app.post("/api/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause an active session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    realtime_service.stop_listening()
    active_sessions[session_id]["status"] = SessionStatus.PAUSED

    return {"session_id": session_id, "status": SessionStatus.PAUSED}

@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a paused session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if active_sessions[session_id]["status"] != SessionStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Session is not paused")

    realtime_service.start_listening()
    active_sessions[session_id]["status"] = SessionStatus.ACTIVE

    return {"session_id": session_id, "status": SessionStatus.ACTIVE}

@app.post("/api/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset session to beginning."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]
    session["current_position"] = 0
    session["accuracy"] = 0.0
    session["feedback_history"] = []

    # Reinitialize real-time service
    realtime_service.initialize(
        reference_surah_text=session["surah"]["text"],
        surah_number=session["config"]["surah_number"],
        word_feedback_callback=lambda f: feedback_queues[session_id].put_nowait(f),
        latency_mode=session["config"]["latency_mode"]
    )

    return {"session_id": session_id, "status": "reset"}

@app.get("/api/sessions/{session_id}", response_model=SessionProgress)
async def get_session_progress(session_id: str):
    """Get current session progress."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]
    progress = realtime_service.get_current_progress()

    return SessionProgress(
        session_id=session_id,
        surah_number=session["config"]["surah_number"],
        current_position=progress["current_position"],
        total_words=progress["total_words"],
        progress_percentage=progress["progress_percentage"],
        accuracy=progress["overall_accuracy"],
        duration=(datetime.now() - datetime.fromisoformat(session["start_time"])).total_seconds(),
        status=session["status"]
    )

@app.get("/api/sessions")
async def get_all_sessions():
    """Get all active sessions."""
    return [
        {
            "session_id": sid,
            "surah_number": s["config"]["surah_number"],
            "status": s["status"],
            "start_time": s["start_time"]
        }
        for sid, s in active_sessions.items()
    ]

# Audio Processing Endpoints
@app.post("/api/audio/submit")
async def submit_audio(
    audio_file: UploadFile = File(...),
    session_id: str = Form(...),
    timestamp: float = Form(...)
):
    """Submit audio chunk for processing."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Read audio data
    audio_data = await audio_file.read()

    # Process audio through hybrid service
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        hybrid_service.transcribe_audio_chunk,
        audio_data,
        timestamp
    )

    # Generate feedback
    feedback = realtime_service.process_transcription(result["text"])

    # Update session
    session = active_sessions[session_id]
    session["feedback_history"].append(feedback)
    session["current_position"] = feedback.get("current_position", 0)
    session["accuracy"] = feedback.get("overall_accuracy", 0.0)

    # Queue feedback for WebSocket delivery
    await feedback_queues[session_id].put(feedback)

    return feedback

@app.post("/api/audio/stream")
async def stream_audio(audio: AudioSubmission, session_id: str = Query(...)):
    """Process streaming audio data."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Decode base64 audio
    audio_bytes = base64.b64decode(audio.audio_data)

    # Process through streaming service
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        realtime_service.process_audio_stream,
        audio_bytes
    )

    return result

# Feedback and Visualization Endpoints
@app.get("/api/sessions/{session_id}/feedback/history")
async def get_feedback_history(
    session_id: str,
    limit: int = Query(default=50, description="Number of feedback items to return")
):
    """Get feedback history for a session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    history = active_sessions[session_id]["feedback_history"]
    return history[-limit:] if len(history) > limit else history

@app.get("/api/sessions/{session_id}/feedback/summary")
async def get_feedback_summary(session_id: str):
    """Get summary of session feedback."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    history = active_sessions[session_id]["feedback_history"]

    # Calculate statistics
    total_words = sum(len(f.get("word_feedback", [])) for f in history)
    correct_words = sum(
        1 for f in history
        for w in f.get("word_feedback", [])
        if w.get("color") == "green"
    )

    return {
        "total_words_processed": total_words,
        "correct_words": correct_words,
        "accuracy": correct_words / total_words if total_words > 0 else 0,
        "common_mistakes": [],  # TODO: Implement with learning service
        "improvement_areas": []  # TODO: Implement with learning service
    }

@app.post("/api/feedback/mode")
async def set_feedback_mode(
    session_id: str = Body(...),
    mode: LatencyMode = Body(...)
):
    """Change feedback mode for a session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    active_sessions[session_id]["config"]["latency_mode"] = mode
    realtime_service.set_latency_mode(mode)

    return {"session_id": session_id, "mode": mode}

# UI Settings and Customization Endpoints
@app.get("/api/settings/ui")
async def get_ui_settings():
    """Get current UI settings."""
    return {
        "color_scheme": ColorScheme().dict(),
        "font_size": 24,
        "show_hints": True,
        "show_tajweed": True,
        "animation_speed": 0.3
    }

@app.post("/api/settings/ui")
async def update_ui_settings(settings: UISettings):
    """Update UI settings."""
    # Store settings (in production, this would be persisted)
    return settings.dict()

@app.get("/api/settings/colors")
async def get_color_scheme():
    """Get current color scheme."""
    return ColorScheme().dict()

@app.post("/api/settings/colors")
async def update_color_scheme(colors: ColorScheme):
    """Update color scheme."""
    return colors.dict()

# Learning and Progress Endpoints
@app.get("/api/learning/stats/{user_id}")
async def get_learning_stats(user_id: str):
    """Get learning statistics for a user."""
    # Initialize a user-specific learning service
    user_learning_service = PersonalizedLearningService(user_id)

    # Return basic stats structure
    return {
        "user_id": user_id,
        "total_sessions": 0,  # TODO: Implement session tracking
        "total_practice_time": 0,
        "accuracy_trend": [],
        "favorite_surahs": []
    }

@app.get("/api/learning/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    """Get personalized learning recommendations."""
    # Initialize a user-specific learning service
    user_learning_service = PersonalizedLearningService(user_id)

    return {
        "user_id": user_id,
        "recommendations": [
            {"type": "review", "surah": 1, "reason": "Practice more frequently"},
            {"type": "new", "surah": 112, "reason": "Short surah for beginners"}
        ]
    }

@app.get("/api/progress/overall/{user_id}")
async def get_overall_progress(user_id: str):
    """Get overall progress for a user."""
    # Return stub data for now
    return {
        "user_id": user_id,
        "total_surahs_practiced": 4,
        "total_practice_time_hours": 12.5,
        "overall_accuracy": 0.85,
        "streak_days": 7,
        "favorite_practice_time": "evening"
    }

@app.get("/api/progress/surah/{user_id}/{surah_number}")
async def get_surah_progress(user_id: str, surah_number: int):
    """Get progress for a specific surah."""
    # Return stub data for now
    return {
        "user_id": user_id,
        "surah_number": surah_number,
        "completion_percentage": 75,
        "accuracy": 0.88,
        "practice_sessions": 15,
        "last_practiced": datetime.now().isoformat()
    }

# WebSocket Endpoint for Real-time Updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            if data["type"] == "ping":
                await websocket.send_json({"type": "pong"})

            elif data["type"] == "get_progress":
                if session_id in active_sessions:
                    progress = realtime_service.get_current_progress()
                    await websocket.send_json({
                        "type": "progress_update",
                        "progress": progress
                    })

            elif data["type"] == "audio_chunk":
                # Process audio chunk
                audio_data = base64.b64decode(data["audio"])
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    realtime_service.process_audio_stream,
                    audio_data
                )
                await websocket.send_json(result)

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        # Don't stop listening since we're not using microphone
        # if session_id in active_sessions:
        #     realtime_service.stop_listening()

# Serve Demo HTML
@app.get("/", response_class=HTMLResponse)
async def serve_demo():
    """Serve the realtime feedback HTML page."""
    html_path = Path(__file__).parent.parent.parent.parent / "templates" / "realtime_feedback.html"
    if html_path.exists():
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Demo HTML not found. Please ensure realtime_feedback.html exists in templates/</h1>")

# Serve Full Demo HTML with all modes
@app.get("/demo", response_class=HTMLResponse)
async def serve_full_demo():
    """Serve the full API demo HTML page with all three modes."""
    html_path = Path(__file__).parent.parent.parent.parent / "templates" / "api_demo.html"
    if html_path.exists():
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Demo HTML not found. Please ensure api_demo.html exists in templates/</h1>")

# Health Check Endpoints
@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Simple health check endpoint for Docker health checks.
    Returns HTTP 200 with minimal JSON response."""
    return JSONResponse(
        status_code=200,
        content={"status": "ok"}
    )

@app.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check endpoint with comprehensive service information."""
    import psutil
    import sys

    # Get system metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
    except Exception as e:
        logger.warning(f"Could not get system metrics: {e}")
        cpu_percent = None
        memory_percent = None
        memory_used_mb = None
        memory_available_mb = None

    # Check service status with error handling
    services_status = {}
    try:
        services_status["realtime"] = "active" if realtime_service else "inactive"
    except Exception as e:
        services_status["realtime"] = f"error: {str(e)}"

    try:
        services_status["hybrid"] = "active" if hybrid_service else "inactive"
    except Exception as e:
        services_status["hybrid"] = f"error: {str(e)}"

    try:
        services_status["metadata"] = "active" if metadata_service else "inactive"
    except Exception as e:
        services_status["metadata"] = f"error: {str(e)}"

    try:
        services_status["learning"] = "active" if learning_service else "inactive"
    except Exception as e:
        services_status["learning"] = f"error: {str(e)}"

    try:
        services_status["progress_tracker"] = "active" if progress_tracker else "inactive"
    except Exception as e:
        services_status["progress_tracker"] = f"error: {str(e)}"

    # Determine overall health status
    overall_status = "healthy"
    if any("error" in status for status in services_status.values()):
        overall_status = "degraded"
    if all("error" in status or status == "inactive" for status in services_status.values()):
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - app_start_time).total_seconds() if 'app_start_time' in globals() else None,
        "services": services_status,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used_mb": memory_used_mb,
            "memory_available_mb": memory_available_mb,
            "python_version": sys.version,
        },
        "active_sessions": len(active_sessions),
        "active_websockets": sum(len(connections) for connections in manager.active_connections.values())
    }

# Export endpoints for testing
@app.get("/api/export/session/{session_id}")
async def export_session(session_id: str, format: str = Query(default="json", enum=["json", "csv"])):
    """Export session data."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    if format == "json":
        return JSONResponse(content=session)
    elif format == "csv":
        # Convert to CSV format
        import csv
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["position", "word", "accuracy", "color"])
        writer.writeheader()

        for feedback in session["feedback_history"]:
            for word in feedback.get("word_feedback", []):
                writer.writerow({
                    "position": word["position"],
                    "word": word["reference_word"],
                    "accuracy": word["confidence"],
                    "color": word["color"]
                })

        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"}
        )


# Helper functions for GPT audio processing
def validate_audio_for_gpt(audio_data: bytes) -> tuple[bool, str]:
    """
    Validate audio data for GPT API submission.

    Args:
        audio_data: Raw audio bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check size (GPT has 25MB limit)
    max_size = 25 * 1024 * 1024  # 25MB
    if len(audio_data) > max_size:
        return False, f"Audio file too large ({len(audio_data) / 1024 / 1024:.1f}MB). Maximum is 25MB."

    # Check minimum size
    if len(audio_data) < 100:
        return False, "Audio file too small or empty"

    return True, ""


def compress_audio_for_gpt(audio_data: bytes) -> tuple[bytes, dict]:
    """
    Compress audio to fit GPT API requirements.

    Args:
        audio_data: Original audio bytes

    Returns:
        Tuple of (compressed_audio, metadata)
    """
    # For now, return original (you could implement actual compression here)
    return audio_data, {"compressed": False}


# GPT Audio Analysis Endpoints
@app.post("/api/audio/analyze/tajweed",
          response_model=TajweedAnalysisAPIResponse,
          tags=["GPT Audio Analysis"],
          summary="Analyze Tajweed Rules in Recitation",
          response_description="Comprehensive Tajweed analysis with scores and recommendations")
async def analyze_tajweed_endpoint(
    request: Request,
    json_request: Optional[TajweedAnalysisRequest] = None,
    audio_file: Optional[UploadFile] = File(None),
    language: Optional[str] = Form(None),
    include_audio_feedback: Optional[bool] = Form(None),
    surah_name: Optional[str] = Form(None),
    surah_number: Optional[int] = Form(None),
    ayah_number: Optional[int] = Form(None)
):
    """
    Analyze Tajweed rules in Quranic recitation using GPT Audio.

    This endpoint accepts audio in two ways:
    1. File upload (multipart/form-data) - Upload an audio file directly
    2. Base64 JSON (application/json) - Send base64 encoded audio in request body

    Returns comprehensive Tajweed analysis including:
    - Detected issues in Makharij, Sifat, Ghunnah, Madd, etc.
    - Scores for different aspects (0-5 scale)
    - Specific feedback with timestamps
    - Recommendations for improvement
    - Optional audio feedback (if requested)

    Example response:
    {
        "success": true,
        "data": {
            "detected_surah": "Al-Fatiha",
            "riwayah": "Hafs",
            "chunks": [...],
            "issues": [...],
            "scores": {
                "makharij": 4.2,
                "sifat": 3.8,
                "ghunnah": 4.5,
                "madd": 4.0,
                "noon_rules": 3.9,
                "overall": 4.1
            },
            "overall_comment": "Good recitation with room for improvement...",
            "next_steps": ["Focus on...", "Practice..."]
        },
        "metadata": {
            "processing_time": 2.5,
            "audio_duration": 15.3,
            "language": "en"
        }
    }
    """
    try:
        start_time = datetime.now()

        # Initialize service if needed
        if not gpt_audio_service.is_initialized:
            gpt_audio_service.initialize()

        # Detect request type based on content type
        content_type = request.headers.get("content-type", "")
        is_json_request = "application/json" in content_type

        # Handle audio input - either from file upload or base64 in request
        audio_data = None
        audio_format = "wav"
        surah_context = None

        if is_json_request:
            # JSON request with base64 audio
            if not json_request:
                # Parse JSON body manually if not already parsed
                body = await request.body()
                import json as json_lib
                json_data = json_lib.loads(body)
                json_request = TajweedAnalysisRequest(**json_data)

            if not json_request.audio_data:
                raise HTTPException(status_code=400, detail="No audio data in JSON request")

            logger.info("Processing Tajweed analysis from base64 audio data")
            audio_data = base64.b64decode(json_request.audio_data)
            audio_format = json_request.audio_format
            language = json_request.language
            include_audio_feedback = json_request.include_audio_feedback
            surah_context = json_request.surah_context
        elif audio_file:
            # Multipart form upload path
            logger.info(f"Processing Tajweed analysis from uploaded file: {audio_file.filename}")
            audio_data = await audio_file.read()
            audio_format = audio_file.filename.split('.')[-1].lower() if '.' in audio_file.filename else "wav"

            # Use form data values, with defaults
            language = language or "en"
            include_audio_feedback = include_audio_feedback or False

            # Build surah context from form data
            if surah_name or surah_number:
                surah_context = {
                    "surah_name": surah_name,
                    "surah_number": surah_number,
                    "ayah_number": ayah_number
                }
        else:
            raise HTTPException(status_code=400, detail="No audio data provided. Send either multipart file upload or JSON with base64 audio.")

        # Validate audio
        is_valid, error_msg = validate_audio_for_gpt(audio_data)
        if not is_valid:
            # Try to compress if too large
            if "too large" in error_msg.lower():
                logger.info("Compressing audio for GPT API submission")
                audio_data, metadata = compress_audio_for_gpt(audio_data)
            else:
                raise HTTPException(status_code=400, detail=f"Audio validation failed: {error_msg}")

        # Validate language
        if language not in ["en", "ar"]:
            raise HTTPException(status_code=400, detail="Language must be 'en' or 'ar'")

        # Perform Tajweed analysis
        logger.info(f"Starting Tajweed analysis with language={language}, audio_feedback={include_audio_feedback}")

        result = await gpt_audio_service.analyze_tajweed(
            audio_input=audio_data,
            language=language,
            surah_context=surah_context,
            include_audio_feedback=include_audio_feedback
        )

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Prepare response
        response_data = result.to_simplified_dict() if hasattr(result, 'to_simplified_dict') else result.__dict__

        return TajweedAnalysisAPIResponse(
            success=True,
            data=response_data,
            metadata={
                "processing_time": processing_time,
                "audio_duration": response_data.get("chunks", [{}])[-1].get("end_time", 0) if response_data.get("chunks") else 0,
                "language": language,
                "has_audio_feedback": include_audio_feedback and result.audio_feedback is not None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tajweed analysis failed: {str(e)}")
        return TajweedAnalysisAPIResponse(
            success=False,
            error=str(e),
            metadata={"timestamp": datetime.now().isoformat()}
        )


@app.post("/api/audio/analyze/recitation",
          response_model=RecitationAnalysisAPIResponse,
          tags=["GPT Audio Analysis"],
          summary="Check Recitation Accuracy",
          response_description="Detailed accuracy analysis comparing recitation to reference text")
async def analyze_recitation_endpoint(
    request: Request,
    json_request: Optional[RecitationAnalysisRequest] = None,
    audio_file: Optional[UploadFile] = File(None),
    reference_text: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    include_audio_feedback: Optional[bool] = Form(None),
    surah_name: Optional[str] = Form(None),
    surah_number: Optional[int] = Form(None),
    ayah_number: Optional[int] = Form(None)
):
    """
    Analyze recitation accuracy against reference Quranic text using GPT Audio.

    This endpoint compares the recited audio against the correct Arabic text to identify:
    - Missed words
    - Added words
    - Mispronounced words
    - Overall accuracy score

    Accepts audio in two ways:
    1. File upload (multipart/form-data) - Upload an audio file directly
    2. Base64 JSON (application/json) - Send base64 encoded audio in request body

    The reference_text parameter should contain the correct Arabic text with proper diacritics.

    Example response:
    {
        "success": true,
        "data": {
            "accuracy_score": 92.5,
            "missed_words": ["word1", "word2"],
            "added_words": [],
            "mispronounced_words": [
                {
                    "word": "الرَّحْمَٰنِ",
                    "timestamp": 2.5,
                    "issue": "Incorrect pronunciation of 'Ra'"
                }
            ],
            "feedback": "Overall good recitation with minor issues...",
            "suggestions": [
                "Practice the pronunciation of 'Ra' with tafkheem",
                "Ensure complete recitation of all words"
            ]
        },
        "metadata": {
            "processing_time": 2.1,
            "reference_length": 15,
            "language": "en"
        }
    }
    """
    try:
        start_time = datetime.now()

        # Initialize service if needed
        if not gpt_audio_service.is_initialized:
            gpt_audio_service.initialize()

        # Detect request type based on content type
        content_type = request.headers.get("content-type", "")
        is_json_request = "application/json" in content_type

        # Handle audio input
        audio_data = None
        audio_format = "wav"
        surah_info = None

        if is_json_request:
            # JSON request with base64 audio
            if not json_request:
                # Parse JSON body manually if not already parsed
                body = await request.body()
                import json as json_lib
                json_data = json_lib.loads(body)
                json_request = RecitationAnalysisRequest(**json_data)

            if not json_request.audio_data:
                raise HTTPException(status_code=400, detail="No audio data in JSON request")

            logger.info("Processing recitation analysis from base64 audio data")
            audio_data = base64.b64decode(json_request.audio_data)
            audio_format = json_request.audio_format
            reference_text = json_request.reference_text
            language = json_request.language
            include_audio_feedback = json_request.include_audio_feedback
            surah_info = json_request.surah_info
        elif audio_file:
            # Multipart form upload path
            logger.info(f"Processing recitation analysis from uploaded file: {audio_file.filename}")
            audio_data = await audio_file.read()
            audio_format = audio_file.filename.split('.')[-1].lower() if '.' in audio_file.filename else "wav"

            # Use form data values, with defaults
            language = language or "en"
            include_audio_feedback = include_audio_feedback or False

            # Build surah info from form data
            if surah_name or surah_number:
                surah_info = {
                    "surah_name": surah_name,
                    "surah_number": surah_number,
                    "ayah_number": ayah_number
                }
        else:
            raise HTTPException(status_code=400, detail="No audio data provided. Send either multipart file upload or JSON with base64 audio.")

        # Validate inputs
        if not reference_text or not reference_text.strip():
            raise HTTPException(status_code=400, detail="Reference text is required")

        # Validate audio
        is_valid, error_msg = validate_audio_for_gpt(audio_data)
        if not is_valid:
            if "too large" in error_msg.lower():
                logger.info("Compressing audio for GPT API submission")
                audio_data, metadata = compress_audio_for_gpt(audio_data)
            else:
                raise HTTPException(status_code=400, detail=f"Audio validation failed: {error_msg}")

        # Validate language
        if language not in ["en", "ar"]:
            raise HTTPException(status_code=400, detail="Language must be 'en' or 'ar'")

        # Perform recitation analysis
        logger.info(f"Starting recitation analysis with language={language}, reference_length={len(reference_text.split())}")

        result = await gpt_audio_service.analyze_recitation(
            audio_input=audio_data,
            reference_text=reference_text,
            language=language,
            surah_info=surah_info,
            include_audio_feedback=include_audio_feedback
        )

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Prepare response
        response_data = result.to_simplified_dict() if hasattr(result, 'to_simplified_dict') else result.__dict__

        return RecitationAnalysisAPIResponse(
            success=True,
            data=response_data,
            metadata={
                "processing_time": processing_time,
                "reference_length": len(reference_text.split()),
                "language": language,
                "has_audio_feedback": include_audio_feedback and result.audio_feedback is not None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recitation analysis failed: {str(e)}")
        return RecitationAnalysisAPIResponse(
            success=False,
            error=str(e),
            metadata={"timestamp": datetime.now().isoformat()}
        )


@app.get("/api/audio/analyze/status",
         tags=["GPT Audio Analysis"],
         summary="Check GPT Audio Service Status")
async def get_analysis_service_status():
    """
    Check the status of the GPT Audio Analysis service.

    Returns information about:
    - Service initialization status
    - Available languages
    - Supported audio formats
    - Configuration status
    """
    try:
        is_initialized = gpt_audio_service.is_initialized

        # Try to test connection if initialized
        connection_ok = False
        if is_initialized:
            try:
                connection_ok = await gpt_audio_service.test_connection()
            except:
                connection_ok = False

        return {
            "service": "GPT Audio Analysis",
            "initialized": is_initialized,
            "connection_status": "connected" if connection_ok else "disconnected",
            "supported_languages": ["en", "ar"],
            "supported_formats": ["wav", "mp3", "m4a", "webm", "ogg"],
            "max_audio_size_mb": 25.0,
            "max_audio_duration_seconds": 300.0,
            "features": {
                "tajweed_analysis": True,
                "recitation_accuracy": True,
                "audio_feedback": True,
                "batch_processing": False  # Not yet implemented
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get service status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get service status")


@app.post("/api/audio/analyze/validate",
          tags=["GPT Audio Analysis"],
          summary="Validate Audio Before Analysis")
async def validate_audio_for_analysis(
    audio_file: UploadFile = File(...),
):
    """
    Validate an audio file for GPT analysis without processing it.

    Useful for pre-flight checks before submitting for analysis.
    Returns validation results including any issues that need to be addressed.
    """
    try:
        audio_data = await audio_file.read()
        audio_format = audio_file.filename.split('.')[-1].lower() if '.' in audio_file.filename else "wav"

        # Perform validation
        is_valid, error_msg = validate_audio_for_gpt(audio_data)

        # Get audio metadata
        from surah_splitter.utils.audio_encoding import _load_audio
        _, metadata = _load_audio(audio_data)

        return {
            "valid": is_valid,
            "error": error_msg if not is_valid else None,
            "metadata": {
                "format": audio_format,
                "size_mb": len(audio_data) / (1024 * 1024),
                "duration_seconds": metadata.get("duration", 0),
                "sample_rate": metadata.get("sample_rate", 0),
                "channels": metadata.get("channels", 0)
            },
            "recommendations": []
        }

        # Add recommendations if needed
        response = {
            "valid": is_valid,
            "error": error_msg if not is_valid else None,
            "metadata": {
                "format": audio_format,
                "size_mb": len(audio_data) / (1024 * 1024),
                "duration_seconds": metadata.get("duration", 0),
                "sample_rate": metadata.get("sample_rate", 0),
                "channels": metadata.get("channels", 0)
            },
            "recommendations": []
        }

        # Add recommendations
        if not is_valid and "too large" in (error_msg or "").lower():
            response["recommendations"].append("Consider compressing the audio or splitting into smaller segments")
        if metadata.get("sample_rate", 0) > 16000:
            response["recommendations"].append("Consider downsampling to 16kHz for optimal processing")

        return response

    except Exception as e:
        logger.error(f"Audio validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)