"""
Web application for real-time Quran recitation feedback.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from surah_splitter.services.realtime_transcription_service import RealtimeTranscriptionService
from surah_splitter.utils.app_logger import logger

app = FastAPI(title="Real-time Quran Recitation Feedback")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """Start background tasks and preload models."""
    logger.info("🚀 Starting up real-time Quran feedback app...")
    
    # Start the feedback processor
    asyncio.create_task(feedback_processor())
    
    # Preload models in background to avoid blocking startup
    asyncio.create_task(preload_models())

async def preload_models():
    """Preload transcription models to avoid delays during sessions."""
    try:
        logger.info("📦 Preloading transcription models...")
        
        # Initialize the hybrid transcription service with models
        from surah_splitter.services.hybrid_transcription_service import HybridTranscriptionService
        preload_service = HybridTranscriptionService()
        
        # This will download and initialize both Azure and local models
        await asyncio.get_event_loop().run_in_executor(
            None, 
            preload_service.initialize
        )
        
        # Store the preloaded service globally
        global preloaded_transcription_service
        preloaded_transcription_service = preload_service
        
        logger.success("✅ Models preloaded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to preload models: {e}")
        logger.warning("⚠️ Models will be loaded on-demand during sessions")

# Global service instances
realtime_service = RealtimeTranscriptionService()
preloaded_transcription_service = None
active_connections: list[WebSocket] = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_feedback(self, feedback: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(feedback))
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)


manager = ConnectionManager()


# Global feedback queue for thread-safe communication
feedback_queue = asyncio.Queue()

def word_feedback_callback(feedback: Dict[str, Any]):
    """Callback function to send feedback to connected clients."""
    # Store feedback in a thread-safe way
    try:
        # Use put_nowait to avoid blocking
        feedback_queue.put_nowait(feedback)
        logger.info(f"✅ Feedback queued: {len(feedback.get('word_feedback', []))} words")
    except asyncio.QueueFull:
        logger.warning("⚠️ Feedback queue is full, dropping feedback")
    except Exception as e:
        logger.error(f"❌ Error queuing feedback: {e}")

async def feedback_processor():
    """Process feedback from the queue and send to clients."""
    while True:
        try:
            # Wait for feedback with timeout
            feedback = await asyncio.wait_for(feedback_queue.get(), timeout=1.0)
            await manager.send_feedback(feedback)
            logger.info(f"📤 Sent feedback to {len(manager.active_connections)} clients")
        except asyncio.TimeoutError:
            # No feedback to process, continue
            continue
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")


@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """Serve the main real-time feedback page."""
    return templates.TemplateResponse("realtime_feedback.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "start_session":
                # Initialize session with reference text
                reference_text = message["reference_text"]
                surah_name = message.get("surah_name", "Unknown")
                surah_number = message.get("surah_number", 1)
                latency_mode = message.get("latency_mode", "balanced")

                logger.info(f"Starting session for {surah_name} (Surah {surah_number}) in {latency_mode} mode")

                # Initialize real-time service with preloaded models if available
                realtime_service.initialize(
                    reference_surah_text=reference_text,
                    surah_number=surah_number,
                    word_feedback_callback=word_feedback_callback,
                    preloaded_service=preloaded_transcription_service,
                    latency_mode=latency_mode
                )
                
                # Start listening
                realtime_service.start_listening()
                
                await websocket.send_text(json.dumps({
                    "type": "session_started",
                    "message": f"Started listening for {surah_name}",
                    "total_words": len(realtime_service.reference_words)
                }))
                
            elif message["type"] == "stop_session":
                # Stop listening
                realtime_service.stop_listening()
                
                await websocket.send_text(json.dumps({
                    "type": "session_stopped",
                    "message": "Stopped listening"
                }))
                
            elif message["type"] == "get_progress":
                # Send current progress
                progress = realtime_service.get_current_progress()
                await websocket.send_text(json.dumps({
                    "type": "progress_update",
                    "progress": progress
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        realtime_service.stop_listening()


@app.get("/api/surahs")
async def get_available_surahs():
    """Get list of available surahs for practice."""
    # This would typically load from your Quran database
    surahs = [
        {
            "number": 1,
            "name": "الفاتحة",
            "english_name": "Al-Fatiha",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ الرَّحْمَٰنِ الرَّحِيمِ مَالِكِ يَوْمِ الدِّينِ إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ"
        },
        {
            "number": 112,
            "name": "الإخلاص",
            "english_name": "Al-Ikhlas",
            "text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
        }
    ]
    return {"surahs": surahs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
