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

### 8. Utility Endpoints

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
    "metadata": "active"
  }
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

## Rate Limiting

- Audio submission: 10 requests per second per session
- WebSocket messages: 100 messages per second per connection
- API endpoints: 100 requests per minute per IP

## Notes

- All text is expected in UTF-8 encoding
- Arabic text should be in standard Quranic script
- Audio formats supported: WAV, MP3, WEBM, OGG
- Maximum audio file size: 10MB
- Session timeout: 30 minutes of inactivity