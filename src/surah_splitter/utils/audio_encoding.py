"""
Audio encoding utilities for Azure GPT Audio API integration.

This module provides functions for encoding audio for submission to the
Azure GPT Audio API and decoding audio responses.
"""

import base64
import io
import os
from pathlib import Path
from typing import Union, Tuple, Dict, Any, Optional
import wave
import struct

import numpy as np
import soundfile as sf
from pydub import AudioSegment

from loguru import logger
from surah_splitter.utils.audio_processing import AudioProcessor


def encode_audio_for_gpt(
    audio_input: Union[str, bytes, Path, np.ndarray],
    target_format: str = "wav",
    sample_rate: int = 16000
) -> Tuple[str, Dict[str, Any]]:
    """
    Encode audio for submission to Azure GPT Audio API.

    Args:
        audio_input: Audio file path, bytes, numpy array, or Path object
        target_format: Target audio format (wav, mp3, etc.)
        sample_rate: Target sample rate in Hz

    Returns:
        Tuple of (base64_encoded_audio, metadata_dict)
    """
    try:
        # Convert input to audio data and metadata
        audio_data, metadata = _load_audio(audio_input)

        # Convert to target format if needed
        if metadata.get('format') != target_format or metadata.get('sample_rate') != sample_rate:
            audio_data, metadata = _convert_audio_format(
                audio_data,
                metadata,
                target_format,
                sample_rate
            )

        # Encode to base64
        base64_audio = base64.b64encode(audio_data).decode('utf-8')

        # Update metadata
        metadata['size_bytes'] = len(audio_data)
        metadata['size_mb'] = len(audio_data) / (1024 * 1024)
        metadata['base64_length'] = len(base64_audio)

        logger.debug(f"Encoded audio: {metadata['duration']:.2f}s, {metadata['size_mb']:.2f}MB")

        return base64_audio, metadata

    except Exception as e:
        logger.error(f"Failed to encode audio for GPT: {str(e)}")
        raise


def decode_gpt_audio_response(
    audio_base64: str,
    output_format: str = "wav"
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Decode audio response from GPT Audio API.

    Args:
        audio_base64: Base64 encoded audio from GPT
        output_format: Desired output format

    Returns:
        Tuple of (audio_bytes, metadata_dict)
    """
    try:
        # Decode base64
        audio_bytes = base64.b64decode(audio_base64)

        # Get audio metadata
        metadata = _get_audio_metadata_from_bytes(audio_bytes)

        # Convert format if needed
        if metadata.get('format') != output_format:
            audio_bytes, metadata = _convert_bytes_to_format(
                audio_bytes,
                output_format
            )

        logger.debug(f"Decoded GPT audio: {metadata.get('duration', 0):.2f}s")

        return audio_bytes, metadata

    except Exception as e:
        logger.error(f"Failed to decode GPT audio response: {str(e)}")
        raise


def _load_audio(audio_input: Union[str, bytes, Path, np.ndarray]) -> Tuple[bytes, Dict[str, Any]]:
    """Load audio from various input types."""
    metadata = {}

    if isinstance(audio_input, (str, Path)):
        # Load from file
        path = Path(audio_input) if isinstance(audio_input, str) else audio_input

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        # Read file
        with open(path, 'rb') as f:
            audio_bytes = f.read()

        # Get file metadata
        metadata['source'] = 'file'
        metadata['filename'] = path.name
        metadata['format'] = path.suffix[1:].lower() if path.suffix else 'unknown'

        # Load with soundfile for detailed metadata
        try:
            data, samplerate = sf.read(str(path))
            metadata['sample_rate'] = samplerate
            metadata['duration'] = len(data) / samplerate
            metadata['channels'] = data.shape[1] if len(data.shape) > 1 else 1
        except Exception as e:
            logger.warning(f"Could not read audio metadata with soundfile: {e}")
            # Try with pydub as fallback
            try:
                audio_seg = AudioSegment.from_file(str(path))
                metadata['sample_rate'] = audio_seg.frame_rate
                metadata['duration'] = len(audio_seg) / 1000.0
                metadata['channels'] = audio_seg.channels
            except Exception as e2:
                logger.warning(f"Could not read audio metadata with pydub: {e2}")

    elif isinstance(audio_input, bytes):
        # Already bytes
        audio_bytes = audio_input
        metadata['source'] = 'bytes'
        metadata.update(_get_audio_metadata_from_bytes(audio_bytes))

    elif isinstance(audio_input, np.ndarray):
        # Convert numpy array to bytes
        audio_bytes = _numpy_to_wav_bytes(audio_input)
        metadata['source'] = 'numpy'
        metadata['format'] = 'wav'
        metadata['sample_rate'] = 16000  # Default assumption
        metadata['duration'] = len(audio_input) / metadata['sample_rate']
        metadata['channels'] = audio_input.shape[1] if len(audio_input.shape) > 1 else 1

    else:
        raise TypeError(f"Unsupported audio input type: {type(audio_input)}")

    return audio_bytes, metadata


def _get_audio_metadata_from_bytes(audio_bytes: bytes) -> Dict[str, Any]:
    """Extract metadata from audio bytes."""
    metadata = {}

    try:
        # Try to load with soundfile from bytes
        with io.BytesIO(audio_bytes) as bio:
            data, samplerate = sf.read(bio)
            metadata['sample_rate'] = samplerate
            metadata['duration'] = len(data) / samplerate
            metadata['channels'] = data.shape[1] if len(data.shape) > 1 else 1
            metadata['format'] = 'wav'  # soundfile typically handles wav

    except Exception as e:
        logger.warning(f"Could not extract metadata from bytes: {e}")
        # Try to detect format from file signature
        if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
            metadata['format'] = 'webm'
        elif audio_bytes[:4] == b'RIFF':
            metadata['format'] = 'wav'
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            metadata['format'] = 'mp3'
        elif len(audio_bytes) > 8 and audio_bytes[4:8] in [b'ftyp', b'ftypM4A ']:
            metadata['format'] = 'mp4'
        else:
            metadata['format'] = 'unknown'

        # Set reasonable defaults
        metadata['sample_rate'] = 16000
        metadata['channels'] = 1
        metadata['duration'] = 10.0  # Default duration estimate

    return metadata


def _convert_audio_format(
    audio_bytes: bytes,
    current_metadata: Dict[str, Any],
    target_format: str,
    target_sample_rate: int
) -> Tuple[bytes, Dict[str, Any]]:
    """Convert audio to target format and sample rate."""
    try:
        # Try to detect format from the audio bytes first
        audio_format = current_metadata.get('format', 'wav')

        # Check for WebM signature
        if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
            audio_format = 'webm'
        # Check for WAV signature
        elif audio_bytes[:4] == b'RIFF':
            audio_format = 'wav'
        # Check for MP3 signature
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            audio_format = 'mp3'
        # Check for M4A/MP4 signature
        elif audio_bytes[4:8] in [b'ftyp', b'ftypM4A ']:
            audio_format = 'mp4'

        # Load audio with pydub
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format=audio_format
        )

        # Convert sample rate if needed
        if target_sample_rate and audio.frame_rate != target_sample_rate:
            audio = audio.set_frame_rate(target_sample_rate)

        # Convert to mono if needed for GPT (usually prefers mono)
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # Export to target format
        output = io.BytesIO()
        audio.export(output, format=target_format)
        converted_bytes = output.getvalue()

        # Update metadata
        new_metadata = current_metadata.copy()
        new_metadata['format'] = target_format
        new_metadata['sample_rate'] = audio.frame_rate
        new_metadata['channels'] = audio.channels
        new_metadata['duration'] = len(audio) / 1000.0

        return converted_bytes, new_metadata

    except Exception as e:
        logger.error(f"Failed to convert audio format: {str(e)}")
        # Return original if conversion fails
        return audio_bytes, current_metadata


def _convert_bytes_to_format(
    audio_bytes: bytes,
    target_format: str
) -> Tuple[bytes, Dict[str, Any]]:
    """Convert audio bytes to a specific format."""
    try:
        # Detect source format
        source_format = 'wav'
        if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
            source_format = 'webm'
        elif audio_bytes[:4] == b'RIFF':
            source_format = 'wav'
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            source_format = 'mp3'
        elif len(audio_bytes) > 8 and audio_bytes[4:8] in [b'ftyp', b'ftypM4A ']:
            source_format = 'mp4'

        # Load with pydub
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)

        # Export to target format
        output = io.BytesIO()
        audio.export(output, format=target_format)
        converted_bytes = output.getvalue()

        # Create metadata
        metadata = {
            'format': target_format,
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'duration': len(audio) / 1000.0
        }

        return converted_bytes, metadata

    except Exception as e:
        logger.error(f"Failed to convert bytes to format: {str(e)}")
        return audio_bytes, {'format': 'unknown'}


def _numpy_to_wav_bytes(
    audio_array: np.ndarray,
    sample_rate: int = 16000
) -> bytes:
    """Convert numpy array to WAV bytes."""
    try:
        # Ensure audio is in the right format
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)

        # Normalize if needed
        if np.abs(audio_array).max() > 1.0:
            audio_array = audio_array / np.abs(audio_array).max()

        # Convert to int16 for WAV
        audio_int16 = (audio_array * 32767).astype(np.int16)

        # Create WAV in memory
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return output.getvalue()

    except Exception as e:
        logger.error(f"Failed to convert numpy array to WAV: {str(e)}")
        raise


def validate_audio_for_gpt(
    audio_input: Union[str, bytes, Path],
    max_size_mb: float = 25.0,
    max_duration_seconds: float = 300.0
) -> Tuple[bool, Optional[str]]:
    """
    Validate audio input for GPT API requirements.

    Args:
        audio_input: The audio to validate
        max_size_mb: Maximum file size in MB
        max_duration_seconds: Maximum duration in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Load audio
        audio_bytes, metadata = _load_audio(audio_input)

        # Check size
        size_mb = len(audio_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Audio too large: {size_mb:.2f}MB (max {max_size_mb}MB)"

        # Check duration
        duration = metadata.get('duration', 0)
        if duration > max_duration_seconds:
            return False, f"Audio too long: {duration:.1f}s (max {max_duration_seconds}s)"

        # Check format
        supported_formats = ['wav', 'mp3', 'm4a', 'webm', 'ogg']
        audio_format = metadata.get('format', 'unknown')
        if audio_format not in supported_formats:
            return False, f"Unsupported format: {audio_format}"

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def compress_audio_for_gpt(
    audio_input: Union[str, bytes, Path],
    target_bitrate: str = "64k",
    target_format: str = "mp3"
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Compress audio to reduce size for GPT API.

    Args:
        audio_input: Audio to compress
        target_bitrate: Target bitrate (e.g., "64k", "128k")
        target_format: Target format for compression

    Returns:
        Tuple of (compressed_bytes, metadata)
    """
    try:
        # Load audio
        audio_bytes, metadata = _load_audio(audio_input)

        # Load with pydub
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format=metadata.get('format', 'wav')
        )

        # Compress
        output = io.BytesIO()
        audio.export(
            output,
            format=target_format,
            bitrate=target_bitrate
        )
        compressed_bytes = output.getvalue()

        # Update metadata
        metadata['format'] = target_format
        metadata['bitrate'] = target_bitrate
        metadata['size_bytes'] = len(compressed_bytes)
        metadata['size_mb'] = len(compressed_bytes) / (1024 * 1024)
        metadata['compression_ratio'] = len(audio_bytes) / len(compressed_bytes)

        logger.info(f"Compressed audio from {len(audio_bytes)/(1024*1024):.2f}MB to {metadata['size_mb']:.2f}MB")

        return compressed_bytes, metadata

    except Exception as e:
        logger.error(f"Failed to compress audio: {str(e)}")
        raise


def extract_audio_segment(
    audio_input: Union[str, bytes, Path],
    start_time: float,
    end_time: float
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Extract a segment from audio.

    Args:
        audio_input: Source audio
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        Tuple of (segment_bytes, metadata)
    """
    try:
        # Load audio
        audio_bytes, metadata = _load_audio(audio_input)

        # Load with pydub
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format=metadata.get('format', 'wav')
        )

        # Extract segment (pydub uses milliseconds)
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)
        segment = audio[start_ms:end_ms]

        # Export segment
        output = io.BytesIO()
        segment.export(output, format='wav')
        segment_bytes = output.getvalue()

        # Update metadata
        segment_metadata = metadata.copy()
        segment_metadata['duration'] = (end_time - start_time)
        segment_metadata['start_time'] = start_time
        segment_metadata['end_time'] = end_time
        segment_metadata['size_bytes'] = len(segment_bytes)
        segment_metadata['size_mb'] = len(segment_bytes) / (1024 * 1024)

        return segment_bytes, segment_metadata

    except Exception as e:
        logger.error(f"Failed to extract audio segment: {str(e)}")
        raise


def get_audio_format_info(audio_format: str) -> Dict[str, Any]:
    """Get information about an audio format."""
    format_info = {
        'wav': {
            'mime_type': 'audio/wav',
            'extension': '.wav',
            'compression': False,
            'quality_loss': False,
            'gpt_supported': True
        },
        'mp3': {
            'mime_type': 'audio/mpeg',
            'extension': '.mp3',
            'compression': True,
            'quality_loss': True,
            'gpt_supported': True
        },
        'm4a': {
            'mime_type': 'audio/mp4',
            'extension': '.m4a',
            'compression': True,
            'quality_loss': True,
            'gpt_supported': True
        },
        'webm': {
            'mime_type': 'audio/webm',
            'extension': '.webm',
            'compression': True,
            'quality_loss': True,
            'gpt_supported': True
        },
        'ogg': {
            'mime_type': 'audio/ogg',
            'extension': '.ogg',
            'compression': True,
            'quality_loss': True,
            'gpt_supported': True
        }
    }

    return format_info.get(audio_format.lower(), {
        'mime_type': 'application/octet-stream',
        'extension': f'.{audio_format}',
        'compression': None,
        'quality_loss': None,
        'gpt_supported': False
    })