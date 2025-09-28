"""
Test client to demonstrate all API endpoints functionality.
Run this after starting the API server.
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any
import requests
import websocket
import threading
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8001"
WS_BASE_URL = "ws://localhost:8001"

class QuranAPIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session_id = None
        self.ws = None

    # Surah Management
    def get_all_surahs(self):
        """Get all available surahs."""
        response = requests.get(f"{self.base_url}/api/surahs")
        return response.json()

    def get_surah(self, surah_number: int):
        """Get specific surah by number."""
        response = requests.get(f"{self.base_url}/api/surahs/{surah_number}")
        return response.json()

    def search_surahs(self, query: str):
        """Search surahs by name."""
        response = requests.get(f"{self.base_url}/api/surahs/search", params={"query": query})
        return response.json()

    # Session Management
    def start_session(self, surah_number: int, latency_mode: str = "balanced"):
        """Start a new recitation session."""
        data = {
            "surah_number": surah_number,
            "latency_mode": latency_mode,
            "enable_tajweed": True,
            "enable_hints": True,
            "difficulty_level": 2
        }
        response = requests.post(f"{self.base_url}/api/sessions/start", json=data)
        result = response.json()
        self.session_id = result.get("session_id")
        return result

    def stop_session(self):
        """Stop the current session."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.post(f"{self.base_url}/api/sessions/{self.session_id}/stop")
        return response.json()

    def pause_session(self):
        """Pause the current session."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.post(f"{self.base_url}/api/sessions/{self.session_id}/pause")
        return response.json()

    def resume_session(self):
        """Resume the current session."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.post(f"{self.base_url}/api/sessions/{self.session_id}/resume")
        return response.json()

    def reset_session(self):
        """Reset the current session."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.post(f"{self.base_url}/api/sessions/{self.session_id}/reset")
        return response.json()

    def get_session_progress(self):
        """Get current session progress."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.get(f"{self.base_url}/api/sessions/{self.session_id}")
        return response.json()

    def get_all_sessions(self):
        """Get all active sessions."""
        response = requests.get(f"{self.base_url}/api/sessions")
        return response.json()

    # Audio Processing
    def submit_audio_file(self, audio_file_path: str):
        """Submit audio file for processing."""
        if not self.session_id:
            return {"error": "No active session"}

        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': f}
            data = {
                'session_id': self.session_id,
                'timestamp': time.time()
            }
            response = requests.post(
                f"{self.base_url}/api/audio/submit",
                files=files,
                data=data
            )
        return response.json()

    def stream_audio_base64(self, audio_data: bytes, format: str = "webm"):
        """Stream audio as base64."""
        if not self.session_id:
            return {"error": "No active session"}

        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        data = {
            "audio_data": audio_b64,
            "format": format,
            "sample_rate": 16000
        }
        response = requests.post(
            f"{self.base_url}/api/audio/stream",
            json=data,
            params={"session_id": self.session_id}
        )
        return response.json()

    # Feedback
    def get_feedback_history(self, limit: int = 50):
        """Get feedback history."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.get(
            f"{self.base_url}/api/sessions/{self.session_id}/feedback/history",
            params={"limit": limit}
        )
        return response.json()

    def get_feedback_summary(self):
        """Get feedback summary."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.get(f"{self.base_url}/api/sessions/{self.session_id}/feedback/summary")
        return response.json()

    def set_feedback_mode(self, mode: str):
        """Set feedback mode."""
        if not self.session_id:
            return {"error": "No active session"}
        data = {
            "session_id": self.session_id,
            "mode": mode
        }
        response = requests.post(f"{self.base_url}/api/feedback/mode", json=data)
        return response.json()

    # UI Settings
    def get_ui_settings(self):
        """Get UI settings."""
        response = requests.get(f"{self.base_url}/api/settings/ui")
        return response.json()

    def update_ui_settings(self, settings: Dict[str, Any]):
        """Update UI settings."""
        response = requests.post(f"{self.base_url}/api/settings/ui", json=settings)
        return response.json()

    def get_color_scheme(self):
        """Get color scheme."""
        response = requests.get(f"{self.base_url}/api/settings/colors")
        return response.json()

    def update_color_scheme(self, colors: Dict[str, str]):
        """Update color scheme."""
        response = requests.post(f"{self.base_url}/api/settings/colors", json=colors)
        return response.json()

    # Learning & Progress
    def get_learning_stats(self, user_id: str):
        """Get learning statistics."""
        response = requests.get(f"{self.base_url}/api/learning/stats/{user_id}")
        return response.json()

    def get_recommendations(self, user_id: str):
        """Get learning recommendations."""
        response = requests.get(f"{self.base_url}/api/learning/recommendations/{user_id}")
        return response.json()

    def get_overall_progress(self, user_id: str):
        """Get overall progress."""
        response = requests.get(f"{self.base_url}/api/progress/overall/{user_id}")
        return response.json()

    def get_surah_progress(self, user_id: str, surah_number: int):
        """Get surah progress."""
        response = requests.get(f"{self.base_url}/api/progress/surah/{user_id}/{surah_number}")
        return response.json()

    # WebSocket Connection
    def connect_websocket(self, on_message_callback=None):
        """Connect to WebSocket for real-time updates."""
        if not self.session_id:
            print("Error: No active session")
            return

        def on_message(ws, message):
            data = json.loads(message)
            print(f"📨 WebSocket message: {data['type']}")
            if on_message_callback:
                on_message_callback(data)

        def on_error(ws, error):
            print(f"❌ WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"🔌 WebSocket closed: {close_msg}")

        def on_open(ws):
            print("✅ WebSocket connected")

        self.ws = websocket.WebSocketApp(
            f"{WS_BASE_URL}/ws/{self.session_id}",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # Run in separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def send_ws_message(self, message: Dict[str, Any]):
        """Send message through WebSocket."""
        if self.ws:
            self.ws.send(json.dumps(message))

    def close_websocket(self):
        """Close WebSocket connection."""
        if self.ws:
            self.ws.close()

    # Utility
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def export_session(self, format: str = "json"):
        """Export session data."""
        if not self.session_id:
            return {"error": "No active session"}
        response = requests.get(
            f"{self.base_url}/api/export/session/{self.session_id}",
            params={"format": format}
        )
        if format == "json":
            return response.json()
        else:
            return response.content

def demo_all_endpoints():
    """Demonstrate all API endpoints."""
    client = QuranAPIClient()

    print("=" * 50)
    print("🕌 Quran Recitation API Demo")
    print("=" * 50)

    # 1. Health Check
    print("\n1️⃣  Health Check")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Services: {health['services']}")

    # 2. Get Surahs
    print("\n2️⃣  Get All Surahs")
    surahs = client.get_all_surahs()
    print(f"   Found {len(surahs)} surahs")

    # 3. Get Specific Surah
    print("\n3️⃣  Get Surah Al-Fatiha")
    surah = client.get_surah(1)
    print(f"   Name: {surah.get('name', 'N/A')}")
    print(f"   English: {surah.get('english_name', 'N/A')}")

    # 4. Search Surahs
    print("\n4️⃣  Search for 'fatiha'")
    search_results = client.search_surahs("fatiha")
    print(f"   Results: {search_results}")

    # 5. Start Session
    print("\n5️⃣  Start Session")
    session = client.start_session(surah_number=1, latency_mode="balanced")
    print(f"   Session ID: {session.get('session_id', 'N/A')}")
    print(f"   Total Words: {session.get('total_words', 0)}")

    # 6. Connect WebSocket
    print("\n6️⃣  Connect WebSocket")
    def handle_ws_message(data):
        print(f"   Received: {data.get('type', 'unknown')}")

    client.connect_websocket(on_message_callback=handle_ws_message)
    time.sleep(1)  # Give it time to connect

    # 7. Get Session Progress
    print("\n7️⃣  Get Session Progress")
    progress = client.get_session_progress()
    print(f"   Position: {progress.get('current_position', 0)}/{progress.get('total_words', 0)}")
    print(f"   Accuracy: {progress.get('accuracy', 0):.2%}")

    # 8. UI Settings
    print("\n8️⃣  Get UI Settings")
    ui_settings = client.get_ui_settings()
    print(f"   Font Size: {ui_settings.get('font_size', 24)}")
    print(f"   Show Hints: {ui_settings.get('show_hints', True)}")

    # 9. Color Scheme
    print("\n9️⃣  Get Color Scheme")
    colors = client.get_color_scheme()
    print(f"   Correct: {colors.get('correct', '#4CAF50')}")
    print(f"   Incorrect: {colors.get('incorrect', '#f44336')}")

    # 10. Update Color Scheme
    print("\n🔟 Update Color Scheme")
    new_colors = {
        "correct": "#00FF00",
        "partial": "#FFFF00",
        "incorrect": "#FF0000",
        "next_expected": "#0000FF",
        "current": "#FF00FF"
    }
    updated_colors = client.update_color_scheme(new_colors)
    print(f"   Updated: {updated_colors}")

    # 11. Set Feedback Mode
    print("\n1️⃣1️⃣  Set Feedback Mode to 'accurate'")
    mode_result = client.set_feedback_mode("accurate")
    print(f"   Mode: {mode_result.get('mode', 'N/A')}")

    # 12. Pause Session
    print("\n1️⃣2️⃣  Pause Session")
    pause_result = client.pause_session()
    print(f"   Status: {pause_result.get('status', 'N/A')}")

    # 13. Resume Session
    print("\n1️⃣3️⃣  Resume Session")
    resume_result = client.resume_session()
    print(f"   Status: {resume_result.get('status', 'N/A')}")

    # 14. Get Feedback History
    print("\n1️⃣4️⃣  Get Feedback History")
    history = client.get_feedback_history(limit=10)
    print(f"   Items: {len(history) if isinstance(history, list) else 0}")

    # 15. Get Feedback Summary
    print("\n1️⃣5️⃣  Get Feedback Summary")
    summary = client.get_feedback_summary()
    print(f"   Accuracy: {summary.get('accuracy', 0):.2%}")

    # 16. Get All Sessions
    print("\n1️⃣6️⃣  Get All Active Sessions")
    all_sessions = client.get_all_sessions()
    print(f"   Active Sessions: {len(all_sessions) if isinstance(all_sessions, list) else 0}")

    # 17. Export Session
    print("\n1️⃣7️⃣  Export Session Data")
    export_data = client.export_session(format="json")
    print(f"   Exported: {'success' if export_data else 'failed'}")

    # 18. Reset Session
    print("\n1️⃣8️⃣  Reset Session")
    reset_result = client.reset_session()
    print(f"   Status: {reset_result.get('status', 'N/A')}")

    # 19. Stop Session
    print("\n1️⃣9️⃣  Stop Session")
    stop_result = client.stop_session()
    print(f"   Status: {stop_result.get('status', 'N/A')}")

    # 20. Close WebSocket
    print("\n2️⃣0️⃣  Close WebSocket")
    client.close_websocket()
    print("   WebSocket closed")

    print("\n" + "=" * 50)
    print("✅ Demo Complete!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        demo_all_endpoints()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server.")
        print("   Please ensure the server is running on http://localhost:8001")
        print("   Start it with: python src/surah_splitter/api/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")