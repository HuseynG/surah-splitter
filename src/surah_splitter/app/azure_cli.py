"""
Azure OpenAI CLI commands for Surah Splitter.
"""

import sys
import json
from pathlib import Path
from typing import Annotated, Optional

from cyclopts import App, Parameter
from rich.console import Console

from surah_splitter.services.azure_transcription_service import AzureTranscriptionService, GPT4TranscriptionService
from surah_splitter.services.hybrid_transcription_service import HybridTranscriptionService
from surah_splitter.utils.app_logger import logger
from surah_splitter.utils.paths import OUTPUTS_PATH
from surah_splitter.utils.file_utils import save_json

# Create cyclopts app and rich console
app = App(help="Process Quran audio files using Azure OpenAI services.")
console = Console()


@app.command(name="azure_transcribe")
def azure_transcribe(
    audio_file: Annotated[Path, Parameter(name=["audio_file", "-au"])],
    azure_endpoint: Annotated[Optional[str], Parameter(name=["--azure-endpoint", "-ae"])] = None,
    api_key: Annotated[Optional[str], Parameter(name=["--api-key", "-ak"])] = None,
    output_file: Annotated[Optional[Path], Parameter(name=["--output-file", "-o"])] = None,
    deployment_name: Annotated[Optional[str], Parameter(name=["--deployment", "-d"])] = None,
    api_version: Annotated[Optional[str], Parameter(name=["--api-version", "-av"])] = None,
):
    """
    Transcribe audio using Azure OpenAI Whisper.

    Args:
        audio_file: Path to the input audio file
        azure_endpoint: Your Azure OpenAI endpoint URL
        api_key: Your Azure OpenAI API key
        output_file: Optional path to save the transcription result
        deployment_name: Name of your Whisper deployment
        api_version: Azure OpenAI API version
    """
    try:
        # Create and initialize service
        service = AzureTranscriptionService()
        service.initialize(azure_endpoint, api_key, api_version, deployment_name)

        # Transcribe audio
        result = service.transcribe_and_align(audio_file, output_file.parent if output_file else None)

        # Save or print result
        if output_file:
            save_json(
                data=result,
                output_dir=output_file.parent,
                filename=output_file.name,
                log_message=f"Azure transcription result saved to {output_file.name}",
            )
        else:
            console.print_json(json.dumps(result, ensure_ascii=False))

        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1


@app.command(name="gpt4_enhance")
def gpt4_enhance(
    audio_file: Annotated[Path, Parameter(name=["audio_file", "-au"])],
    azure_endpoint: Annotated[str, Parameter(name=["--azure-endpoint", "-ae"])],
    api_key: Annotated[str, Parameter(name=["--api-key", "-ak"])],
    output_file: Annotated[Optional[Path], Parameter(name=["--output-file", "-o"])] = None,
    reference_text: Annotated[Optional[str], Parameter(name=["--reference-text", "-rt"])] = None,
    whisper_deployment: Annotated[str, Parameter(name=["--whisper-deployment", "-wd"])] = "whisper-1",
    gpt_deployment: Annotated[str, Parameter(name=["--gpt-deployment", "-gd"])] = "gpt-4o-mini",
):
    """
    Transcribe with Whisper and enhance with GPT-4o-mini.

    Args:
        audio_file: Path to the input audio file
        azure_endpoint: Your Azure OpenAI endpoint URL
        api_key: Your Azure OpenAI API key
        output_file: Optional path to save the enhanced result
        reference_text: Optional reference Quran text for comparison
        whisper_deployment: Name of your Whisper deployment
        gpt_deployment: Name of your GPT-4o-mini deployment
    """
    try:
        # Create and initialize service
        service = GPT4TranscriptionService()
        service.initialize(azure_endpoint, api_key, whisper_deployment=whisper_deployment, gpt_deployment=gpt_deployment)

        # Transcribe and enhance
        result = service.transcribe_and_enhance(audio_file, reference_text)

        # Save or print result
        if output_file:
            save_json(
                data=result,
                output_dir=output_file.parent,
                filename=output_file.name,
                log_message=f"Enhanced transcription result saved to {output_file.name}",
            )
        else:
            console.print_json(json.dumps(result, ensure_ascii=False))

        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1


@app.command(name="hybrid_transcribe")
def hybrid_transcribe(
    audio_file: Annotated[Path, Parameter(name=["audio_file", "-au"])],
    output_file: Annotated[Optional[Path], Parameter(name=["--output-file", "-o"])] = None,
    azure_endpoint: Annotated[Optional[str], Parameter(name=["--azure-endpoint", "-ae"])] = None,
    api_key: Annotated[Optional[str], Parameter(name=["--api-key", "-ak"])] = None,
    deployment_name: Annotated[Optional[str], Parameter(name=["--deployment", "-d"])] = None,
    local_model: Annotated[str, Parameter(name=["--local-model", "-lm"])] = "OdyAsh/faster-whisper-base-ar-quran",
    device: Annotated[Optional[str], Parameter(name=["--device", "-dev"])] = None,
):
    """
    Hybrid transcription: Azure quality + local word timing.

    Args:
        audio_file: Path to the input audio file
        output_file: Optional path to save the transcription result
        azure_endpoint: Your Azure OpenAI endpoint URL
        api_key: Your Azure OpenAI API key
        deployment_name: Name of your Azure deployment
        local_model: Local model for word-level timing
        device: Device for local model (cpu/cuda)
    """
    try:
        # Create and initialize hybrid service
        service = HybridTranscriptionService()
        service.initialize(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            deployment_name=deployment_name,
            local_model_name=local_model,
            device=device
        )

        # Transcribe with hybrid approach
        result = service.transcribe_and_align(audio_file, output_file.parent if output_file else None)

        # Save or print result
        if output_file:
            save_json(
                data=result,
                output_dir=output_file.parent,
                filename=output_file.name,
                log_message=f"Hybrid transcription result saved to {output_file.name}",
            )
        else:
            console.print_json(json.dumps(result, ensure_ascii=False))

        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1


def main():
    """Run the Azure OpenAI CLI application."""
    return app()


if __name__ == "__main__":
    sys.exit(main())
