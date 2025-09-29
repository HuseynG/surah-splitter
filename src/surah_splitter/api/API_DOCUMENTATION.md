# Quran Recitation Feedback API Documentation

## Base URL
```
http://localhost:8001
```

## Authentication
Currently no authentication required (add JWT/OAuth2 in production)

## Endpoints

### 1. Surah Management

#### Get All Surahs
```http
GET /api/surahs
```
**Response:**
```json
[
  {
    "number": 1,
    "name": "الفاتحة",
    "english_name": "Al-Fatiha",
    "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ...",
    "total_ayahs": 7,
    "revelation_type": "Meccan"
  }
]
```

#### Get Specific Surah
```http
GET /api/surahs/{surah_number}
```
**Example:** `/api/surahs/1`

#### Search Surahs
```http
GET /api/surahs/search?query=fatiha
```

### 2. Session Management

#### Start Session
```http
POST /api/sessions/start
```
**Request Body:**
```json
{
  "surah_number": 1,
  "latency_mode": "balanced",
  "enable_tajweed": true,
  "enable_hints": true,
  "difficulty_level": 2
}
```
**Response:**
```json
{
  "session_id": "session_1234567890",
  "surah": {...},
  "total_words": 29,
  "status": "active"
}
```

#### Stop Session
```http
POST /api/sessions/{session_id}/stop
```

#### Pause Session
```http
POST /api/sessions/{session_id}/pause
```

#### Resume Session
```http
POST /api/sessions/{session_id}/resume
```

#### Reset Session
```http
POST /api/sessions/{session_id}/reset
```

#### Get Session Progress
```http
GET /api/sessions/{session_id}
```
**Response:**
```json
{
  "session_id": "session_1234567890",
  "surah_number": 1,
  "current_position": 15,
  "total_words": 29,
  "progress_percentage": 51.72,
  "accuracy": 0.87,
  "duration": 120.5,
  "status": "active"
}
```

#### Get All Active Sessions
```http
GET /api/sessions
```

### 3. Audio Processing

#### Submit Audio File
```http
POST /api/audio/submit
```
**Request:** `multipart/form-data`
- `audio_file`: Audio file (WAV/MP3/WEBM)
- `session_id`: Session ID string
- `timestamp`: Float timestamp

**Response:**
```json
{
  "word_feedback": [
    {
      "position": 0,
      "reference_word": "بِسْمِ",
      "transcribed_word": "بسم",
      "confidence": 0.92,
      "color": "green",
      "hint": null,
      "tajweed_issues": []
    }
  ],
  "overall_accuracy": 0.85,
  "current_position": 5
}
```

#### Stream Audio (Base64)
```http
POST /api/audio/stream?session_id={session_id}
```
**Request Body:**
```json
{
  "audio_data": "base64_encoded_audio_string",
  "format": "webm",
  "sample_rate": 16000
}
```

### 4. Feedback & Visualization

#### Get Feedback History
```http
GET /api/sessions/{session_id}/feedback/history?limit=50
```

#### Get Feedback Summary
```http
GET /api/sessions/{session_id}/feedback/summary
```
**Response:**
```json
{
  "total_words_processed": 150,
  "correct_words": 127,
  "accuracy": 0.847,
  "common_mistakes": [
    {"word": "الرَّحْمَٰنِ", "error_count": 3}
  ],
  "improvement_areas": [
    "Tajweed rules for Madd",
    "Pronunciation of heavy letters"
  ]
}
```

#### Set Feedback Mode
```http
POST /api/feedback/mode
```
**Request Body:**
```json
{
  "session_id": "session_1234567890",
  "mode": "accurate"
}
```
**Modes:** `instant`, `balanced`, `accurate`

### 5. UI Settings

#### Get UI Settings
```http
GET /api/settings/ui
```

#### Update UI Settings
```http
POST /api/settings/ui
```
**Request Body:**
```json
{
  "color_scheme": {
    "correct": "#4CAF50",
    "partial": "#FFC107",
    "incorrect": "#f44336",
    "next_expected": "#2196F3",
    "current": "#FFFF00"
  },
  "font_size": 24,
  "show_hints": true,
  "show_tajweed": true,
  "animation_speed": 0.3
}
```

#### Get Color Scheme
```http
GET /api/settings/colors
```

#### Update Color Scheme
```http
POST /api/settings/colors
```
**Request Body:**
```json
{
  "correct": "#4CAF50",
  "partial": "#FFC107",
  "incorrect": "#f44336",
  "next_expected": "#2196F3",
  "current": "#FFFF00"
}
```

### 6. Learning & Progress

#### Get Learning Statistics
```http
GET /api/learning/stats/{user_id}
```

#### Get Recommendations
```http
GET /api/learning/recommendations/{user_id}
```

#### Get Overall Progress
```http
GET /api/progress/overall/{user_id}
```

#### Get Surah Progress
```http
GET /api/progress/surah/{user_id}/{surah_number}
```

### 7. WebSocket Connection

#### Connect to Real-time Updates
```ws
ws://localhost:8001/ws/{session_id}
```

**Send Messages:**
```json
{
  "type": "ping"
}
```

```json
{
  "type": "get_progress"
}
```

```json
{
  "type": "audio_chunk",
  "audio": "base64_encoded_audio"
}
```

**Receive Messages:**
```json
{
  "type": "word_feedback",
  "word_feedback": [...],
  "overall_accuracy": 0.85,
  "current_position": 10
}
```

```json
{
  "type": "progress_update",
  "progress": {
    "current_position": 15,
    "total_words": 29,
    "progress_percentage": 51.72,
    "overall_accuracy": 0.87
  }
}
```

### 8. GPT Audio Analysis Endpoints

#### Tajweed Analysis
```http
POST /api/audio/analyze/tajweed
```

Analyzes Tajweed rules in Quranic recitation using Azure GPT Audio models. Provides comprehensive feedback on pronunciation, rules application, and areas for improvement.

**Method 1: File Upload (multipart/form-data)**

**Request:**
- `audio_file`: Audio file (WAV/MP3/M4A/WEBM/OGG, max 25MB)
- `language`: Feedback language (`en` or `ar`, optional, default: `en`)
- `include_audio_feedback`: Return audio feedback (`true`/`false`, optional, default: `false`)
- `surah_name`: Surah name (optional, for context)
- `surah_number`: Surah number (optional, for context)
- `ayah_number`: Ayah number (optional, for context)

**Method 2: JSON with Base64 Audio (application/json)**

**Request Body:**
```json
{
  "audio_data": "base64_encoded_audio_string",
  "audio_format": "wav",
  "language": "en",
  "include_audio_feedback": false,
  "surah_context": {
    "surah_name": "Al-Fatiha",
    "surah_number": 1,
    "ayah_number": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "detected_surah": "Al-Fatiha",
    "riwayah": "Hafs",
    "chunks": [
      {
        "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "start_time": 0.0,
        "end_time": 3.5,
        "issues": ["Minor Ghunnah duration"],
        "correct_application": ["Proper Madd application"]
      }
    ],
    "issues": [
      {
        "category": "GHUNNAH",
        "rule": "Ghunnah Duration",
        "word": "الرَّحْمَٰنِ",
        "timestamp": 2.1,
        "severity": "LOW",
        "description": "Ghunnah should be held for 2 counts",
        "correction": "Extend the nasal sound to full 2-count duration"
      }
    ],
    "scores": {
      "makharij": 4.2,
      "sifat": 3.8,
      "ghunnah": 4.5,
      "madd": 4.0,
      "noon_rules": 3.9,
      "overall": 4.1
    },
    "overall_comment": "Good recitation with minor areas for improvement. Focus on maintaining consistent Ghunnah duration.",
    "next_steps": [
      "Practice Ghunnah exercises with 2-count timing",
      "Review Noon Sakinah rules with a teacher"
    ],
    "audio_feedback": {
      "text_feedback": "Your recitation shows good understanding...",
      "audio_base64": "base64_encoded_audio_feedback",
      "audio_format": "wav"
    },
    "timestamp": "2024-01-15T10:30:00"
  },
  "metadata": {
    "processing_time": 2.5,
    "audio_duration": 15.3,
    "language": "en"
  }
}
```

#### Recitation Accuracy Analysis
```http
POST /api/audio/analyze/recitation
```

Compares recitation against reference Arabic text to check accuracy, identify missed/added words, and provide improvement suggestions.

**Method 1: File Upload (multipart/form-data)**

**Request:**
- `audio_file`: Audio file (WAV/MP3/M4A/WEBM/OGG, max 25MB)
- `reference_text`: Arabic reference text (required)
- `language`: Feedback language (`en` or `ar`, optional, default: `en`)
- `include_audio_feedback`: Return audio feedback (`true`/`false`, optional, default: `false`)
- `surah_name`: Surah name (optional, for context)
- `surah_number`: Surah number (optional, for context)
- `ayah_number`: Ayah number (optional, for context)

**Method 2: JSON with Base64 Audio (application/json)**

**Request Body:**
```json
{
  "audio_data": "base64_encoded_audio_string",
  "audio_format": "wav",
  "reference_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
  "language": "ar",
  "include_audio_feedback": true,
  "surah_info": {
    "surah_name": "Al-Fatiha",
    "surah_number": 1,
    "ayah_number": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "accuracy_score": 87.5,
    "missed_words": ["الْعَالَمِينَ"],
    "added_words": [],
    "mispronounced_words": [
      {
        "word": "الرَّحِيمِ",
        "timestamp": 3.2,
        "issue": "Incorrect vowel length on 'حِي'"
      }
    ],
    "feedback": "Good recitation with 87.5% accuracy. Focus on the pronunciation of 'الرَّحِيمِ' and ensure you don't miss 'الْعَالَمِينَ'.",
    "suggestions": [
      "Practice the pronunciation of 'الرَّحِيمِ' with proper vowel lengths",
      "Review the complete verse to avoid omissions",
      "Consider slowing down slightly for better accuracy"
    ],
    "audio_feedback": {
      "text_feedback": "ما شاء الله، قراءة جيدة...",
      "audio_base64": "base64_encoded_audio_feedback",
      "audio_format": "wav"
    },
    "timestamp": "2024-01-15T10:35:00"
  },
  "metadata": {
    "processing_time": 3.1,
    "audio_duration": 12.5,
    "language": "ar",
    "reference_length": 29
  }
}
```

#### Validate Audio File
```http
POST /api/audio/analyze/validate
```

Validates audio file before analysis to ensure it meets requirements.

**Request:** `multipart/form-data`
- `audio_file`: Audio file to validate

**Response:**
```json
{
  "valid": true,
  "format": "wav",
  "duration": 15.3,
  "size_mb": 2.4,
  "sample_rate": 16000,
  "channels": 1,
  "issues": []
}
```

**Error Response:**
```json
{
  "valid": false,
  "issues": [
    "File size exceeds 25MB limit",
    "Audio duration exceeds 5 minutes"
  ]
}
```

#### GPT Audio Service Status
```http
GET /api/audio/analyze/status
```

Check GPT Audio service health and configuration.

**Response:**
```json
{
  "service": "GPT Audio Analysis",
  "initialized": true,
  "connection_status": "connected",
  "supported_languages": ["en", "ar"],
  "supported_formats": ["wav", "mp3", "m4a", "webm", "ogg"],
  "max_audio_size_mb": 25.0,
  "max_audio_duration_seconds": 300.0,
  "features": {
    "tajweed_analysis": true,
    "recitation_accuracy": true,
    "audio_feedback": true,
    "batch_processing": false
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

### 9. Utility Endpoints

#### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "services": {
    "realtime": "active",
    "hybrid": "active",
    "metadata": "active",
    "gpt_audio": "active"
  }
}
```

#### Detailed Health Check
```http
GET /health/detailed
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "uptime_seconds": 3600,
  "services": {
    "realtime": "active",
    "hybrid": "active",
    "metadata": "active",
    "gpt_audio": "active"
  },
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "memory_used_mb": 512.3,
    "memory_available_mb": 1024.7,
    "python_version": "3.11.0"
  },
  "active_sessions": 3,
  "active_websockets": 2
}
```

#### Export Session Data
```http
GET /api/export/session/{session_id}?format=json
```
**Formats:** `json`, `csv`

## WebSocket Events

### Client to Server Events

1. **start_session**
```json
{
  "type": "start_session",
  "reference_text": "بِسْمِ اللَّهِ...",
  "surah_name": "الفاتحة",
  "surah_number": 1,
  "latency_mode": "balanced"
}
```

2. **stop_session**
```json
{
  "type": "stop_session"
}
```

3. **get_progress**
```json
{
  "type": "get_progress"
}
```

### Server to Client Events

1. **session_started**
```json
{
  "type": "session_started",
  "message": "Started listening for Al-Fatiha",
  "total_words": 29
}
```

2. **word_feedback**
```json
{
  "type": "word_feedback",
  "word_feedback": [...],
  "overall_accuracy": 0.85,
  "current_position": 10
}
```

3. **progress_update**
```json
{
  "type": "progress_update",
  "progress": {...}
}
```

## Error Responses

### 404 Not Found
```json
{
  "detail": "Session not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Session is not paused"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Usage Examples

### JavaScript/TypeScript Client

```javascript
// Start a session
const response = await fetch('http://localhost:8001/api/sessions/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    surah_number: 1,
    latency_mode: 'balanced',
    enable_tajweed: true,
    enable_hints: true,
    difficulty_level: 2
  })
});
const { session_id } = await response.json();

// Connect WebSocket
const ws = new WebSocket(`ws://localhost:8001/ws/${session_id}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'word_feedback') {
    // Update UI with word feedback
    updateWordHighlighting(data.word_feedback);
  }
};

// Submit audio
const formData = new FormData();
formData.append('audio_file', audioBlob);
formData.append('session_id', session_id);
formData.append('timestamp', Date.now());

await fetch('http://localhost:8001/api/audio/submit', {
  method: 'POST',
  body: formData
});
```

### Python Client

```python
import requests
import websocket
import json

# Start session
response = requests.post('http://localhost:8001/api/sessions/start', json={
    'surah_number': 1,
    'latency_mode': 'balanced',
    'enable_tajweed': True,
    'enable_hints': True,
    'difficulty_level': 2
})
session_data = response.json()
session_id = session_data['session_id']

# Connect WebSocket
ws = websocket.WebSocketApp(
    f"ws://localhost:8001/ws/{session_id}",
    on_message=lambda ws, msg: handle_message(json.loads(msg))
)

# Submit audio
files = {'audio_file': open('recording.wav', 'rb')}
data = {
    'session_id': session_id,
    'timestamp': time.time()
}
response = requests.post(
    'http://localhost:8001/api/audio/submit',
    files=files,
    data=data
)
```

## GPT Audio Analysis Details

### Supported Audio Formats
- **WAV**: Uncompressed, best quality (recommended)
- **MP3**: Compressed, widely supported
- **M4A**: Apple format, good compression
- **WEBM**: Web-optimized format
- **OGG**: Open-source compressed format

### Audio Requirements
- **Maximum file size**: 25MB
- **Maximum duration**: 5 minutes (300 seconds)
- **Recommended sample rate**: 16kHz or higher
- **Channels**: Mono or stereo (mono preferred for smaller size)
- **Bit rate**: 128kbps minimum for compressed formats

### Language Support
- **English (`en`)**: Full feedback in English with transliteration
- **Arabic (`ar`)**: Native Arabic feedback with proper RTL formatting

### Tajweed Categories
- **MAKHARIJ**: Points of articulation
- **SIFAT**: Characteristics of letters
- **GHUNNAH**: Nasalization rules
- **MADD**: Elongation rules
- **NOON_RULES**: Rules for Noon Sakinah and Tanween
- **QALQALAH**: Echo/bounce effect
- **OTHER**: Miscellaneous rules

### Error Codes (GPT Audio Specific)
- **422**: Invalid audio format or parameters
- **413**: Audio file too large (>25MB)
- **400**: Missing required parameters (e.g., reference_text for recitation)
- **408**: Analysis timeout (>60 seconds)
- **503**: GPT Audio service unavailable
- **429**: Rate limit exceeded

## Rate Limiting

- **GPT Audio Analysis**: 5 requests per minute per session
- **Audio submission**: 10 requests per second per session
- **WebSocket messages**: 100 messages per second per connection
- **API endpoints**: 100 requests per minute per IP

## Notes

- All text is expected in UTF-8 encoding
- Arabic text should be in standard Quranic script
- Audio formats supported: WAV, MP3, M4A, WEBM, OGG
- Maximum audio file size: 25MB (GPT Audio), 10MB (regular)
- Session timeout: 30 minutes of inactivity
- GPT Audio analysis may take 2-10 seconds depending on audio length
- Audio feedback adds ~2 seconds to processing time