"""
CLI for running the real-time Quran recitation feedback web application.
"""

import sys
import subprocess
from pathlib import Path
from typing import Annotated, Optional

from cyclopts import App, Parameter
import uvicorn

from surah_splitter.utils.app_logger import logger

# Create cyclopts app
app = App(help="Real-time Quran recitation feedback application.")


@app.command(name="serve")
def serve_web_app(
    host: Annotated[str, Parameter(name=["--host", "-h"])] = "0.0.0.0",
    port: Annotated[int, Parameter(name=["--port", "-p"])] = 8000,
    reload: Annotated[bool, Parameter(name=["--reload", "-r"])] = False,
):
    """
    Start the real-time feedback web application.

    Args:
        host: Host to bind the server to
        port: Port to run the server on
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting real-time feedback web app on {host}:{port}")
    
    try:
        # Import the FastAPI app
        from surah_splitter.web.realtime_app import app as fastapi_app
        
        # Run with uvicorn
        uvicorn.run(
            "surah_splitter.web.realtime_app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"Failed to start web application: {e}")
        return 1


@app.command(name="test_audio")
def test_audio_setup():
    """
    Test audio input setup for real-time transcription.
    """
    logger.info("Testing audio input setup...")
    
    try:
        import sounddevice as sd
        import numpy as np
        
        # List available audio devices
        logger.info("Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                logger.info(f"  {i}: {device['name']} (Input channels: {device['max_input_channels']})")
        
        # Test recording
        logger.info("Testing 3-second recording...")
        duration = 3  # seconds
        sample_rate = 16000
        
        logger.info("Recording... Speak now!")
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
        sd.wait()  # Wait until recording is finished
        
        # Check if we got audio
        max_amplitude = np.max(np.abs(audio_data))
        logger.info(f"Recording complete. Max amplitude: {max_amplitude:.4f}")
        
        if max_amplitude > 0.01:
            logger.success("✅ Audio input is working correctly!")
        else:
            logger.warning("⚠️  Very low audio level detected. Check your microphone.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Audio test failed: {e}")
        logger.error("Make sure you have a working microphone and audio drivers installed.")
        return 1


@app.command(name="setup")
def setup_realtime_environment():
    """
    Set up the environment for real-time transcription.
    """
    logger.info("Setting up real-time transcription environment...")
    
    # Check if required directories exist
    template_dir = Path("templates")
    static_dir = Path("static")
    
    if not template_dir.exists():
        logger.info("Creating templates directory...")
        template_dir.mkdir(exist_ok=True)
    
    if not static_dir.exists():
        logger.info("Creating static directory...")
        static_dir.mkdir(exist_ok=True)
    
    # Test imports
    try:
        import sounddevice
        import soundfile
        import fastapi
        import uvicorn
        logger.success("✅ All required packages are installed")
    except ImportError as e:
        logger.error(f"❌ Missing required package: {e}")
        logger.info("Run 'uv sync' to install missing dependencies")
        return 1
    
    # Test Azure connection (if configured)
    try:
        from surah_splitter.services.azure_transcription_service import AzureTranscriptionService
        service = AzureTranscriptionService()
        service.initialize()  # This will use environment variables
        logger.success("✅ Azure OpenAI connection configured")
    except Exception as e:
        logger.warning(f"⚠️  Azure OpenAI not configured: {e}")
        logger.info("Make sure to set your Azure credentials in .env file")
    
    logger.success("Setup complete! Run 'uv run python -m src.surah_splitter.app.realtime_cli serve' to start the web app")
    return 0


def main():
    """Run the real-time CLI application."""
    return app()


if __name__ == "__main__":
    sys.exit(main())
