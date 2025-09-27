"""
Audio processing utilities for improved real-time transcription.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional
import webrtcvad
from surah_splitter.utils.app_logger import logger


class AudioProcessor:
    """Advanced audio processing for real-time transcription."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(2)  # Moderate aggressiveness (0-3)

        # Noise reduction parameters
        self.noise_profile = None
        self.noise_gate_threshold = 0.02

        # Auto-gain parameters
        self.target_rms = 0.1
        self.max_gain = 5.0
        self.min_gain = 0.5

        # High-pass filter to remove low-frequency noise
        self.highpass_freq = 80  # Hz
        self.setup_filters()

    def setup_filters(self):
        """Setup audio filters."""
        # High-pass filter
        nyquist = self.sample_rate / 2
        normal_cutoff = self.highpass_freq / nyquist
        self.highpass_b, self.highpass_a = signal.butter(
            4, normal_cutoff, btype='high', analog=False
        )

    def apply_noise_reduction(self, audio: np.ndarray, update_profile: bool = False) -> np.ndarray:
        """
        Apply spectral noise reduction.

        Args:
            audio: Input audio signal
            update_profile: Whether to update noise profile from this audio

        Returns:
            Noise-reduced audio
        """
        # Convert to frequency domain
        f, t, Zxx = signal.stft(audio, fs=self.sample_rate, nperseg=512)

        # Update noise profile if requested (from quiet periods)
        if update_profile and len(audio) > self.sample_rate * 0.5:
            # Use first 0.5 seconds as noise profile
            noise_segment = audio[:int(self.sample_rate * 0.5)]
            _, _, noise_Zxx = signal.stft(noise_segment, fs=self.sample_rate, nperseg=512)
            self.noise_profile = np.mean(np.abs(noise_Zxx), axis=1)

        # Apply spectral subtraction if we have a noise profile
        if self.noise_profile is not None:
            # Expand noise profile to match Zxx shape
            noise_expanded = self.noise_profile[:, np.newaxis]

            # Spectral subtraction
            magnitude = np.abs(Zxx)
            phase = np.angle(Zxx)

            # Subtract noise profile
            clean_magnitude = magnitude - 0.8 * noise_expanded
            clean_magnitude = np.maximum(clean_magnitude, 0.1 * magnitude)  # Avoid over-subtraction

            # Reconstruct complex spectrum
            Zxx_clean = clean_magnitude * np.exp(1j * phase)
        else:
            Zxx_clean = Zxx

        # Convert back to time domain
        _, audio_clean = signal.istft(Zxx_clean, fs=self.sample_rate)

        return audio_clean.astype(np.float32)

    def apply_voice_activity_detection(self, audio: np.ndarray, frame_duration_ms: int = 30) -> Tuple[np.ndarray, bool]:
        """
        Apply voice activity detection to filter out non-speech.

        Args:
            audio: Input audio signal
            frame_duration_ms: Frame duration for VAD (10, 20, or 30 ms)

        Returns:
            Tuple of (processed audio, has_speech)
        """
        # Ensure audio is in the right format for VAD
        audio_int16 = (audio * 32767).astype(np.int16)

        frame_length = int(self.sample_rate * frame_duration_ms / 1000)
        num_frames = len(audio_int16) // frame_length

        speech_frames = []
        has_speech = False

        for i in range(num_frames):
            start = i * frame_length
            end = start + frame_length
            frame = audio_int16[start:end]

            # Check if frame contains speech
            is_speech = self.vad.is_speech(frame.tobytes(), self.sample_rate)

            if is_speech:
                has_speech = True
                speech_frames.extend(frame)
            else:
                # Add silence for non-speech frames
                speech_frames.extend(np.zeros_like(frame))

        # Handle remaining samples
        if len(audio_int16) > num_frames * frame_length:
            remaining = audio_int16[num_frames * frame_length:]
            speech_frames.extend(remaining)

        # Convert back to float32
        processed_audio = np.array(speech_frames, dtype=np.float32) / 32767.0

        return processed_audio, has_speech

    def apply_auto_gain_control(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply automatic gain control to normalize audio levels.

        Args:
            audio: Input audio signal

        Returns:
            Gain-adjusted audio
        """
        # Calculate RMS
        rms = np.sqrt(np.mean(audio ** 2))

        if rms > 0:
            # Calculate gain needed
            gain = self.target_rms / rms

            # Clip gain to reasonable range
            gain = np.clip(gain, self.min_gain, self.max_gain)

            # Apply gain with soft clipping
            audio_gained = audio * gain
            audio_gained = np.tanh(audio_gained * 0.5) * 2  # Soft clipping

            return audio_gained

        return audio

    def apply_highpass_filter(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply high-pass filter to remove low-frequency noise.

        Args:
            audio: Input audio signal

        Returns:
            Filtered audio
        """
        return signal.filtfilt(self.highpass_b, self.highpass_a, audio).astype(np.float32)

    def process_audio(
        self,
        audio: np.ndarray,
        enable_noise_reduction: bool = True,
        enable_vad: bool = True,
        enable_agc: bool = True,
        enable_highpass: bool = True
    ) -> Tuple[np.ndarray, dict]:
        """
        Apply full audio processing pipeline.

        Args:
            audio: Input audio signal
            enable_noise_reduction: Enable spectral noise reduction
            enable_vad: Enable voice activity detection
            enable_agc: Enable automatic gain control
            enable_highpass: Enable high-pass filtering

        Returns:
            Tuple of (processed audio, processing info dict)
        """
        info = {
            'has_speech': True,
            'gain_applied': 1.0,
            'noise_reduced': False
        }

        # Apply high-pass filter first
        if enable_highpass:
            audio = self.apply_highpass_filter(audio)

        # Apply noise reduction
        if enable_noise_reduction:
            audio = self.apply_noise_reduction(audio)
            info['noise_reduced'] = True

        # Apply AGC
        if enable_agc:
            original_rms = np.sqrt(np.mean(audio ** 2))
            audio = self.apply_auto_gain_control(audio)
            new_rms = np.sqrt(np.mean(audio ** 2))
            if original_rms > 0:
                info['gain_applied'] = new_rms / original_rms

        # Apply VAD
        if enable_vad:
            audio, has_speech = self.apply_voice_activity_detection(audio)
            info['has_speech'] = has_speech

        return audio, info

    def detect_clipping(self, audio: np.ndarray, threshold: float = 0.99) -> float:
        """
        Detect audio clipping.

        Args:
            audio: Input audio signal
            threshold: Clipping threshold

        Returns:
            Percentage of clipped samples
        """
        clipped_samples = np.sum(np.abs(audio) >= threshold)
        total_samples = len(audio)

        return (clipped_samples / total_samples) * 100 if total_samples > 0 else 0

    def get_audio_stats(self, audio: np.ndarray) -> dict:
        """
        Get audio statistics for monitoring.

        Args:
            audio: Input audio signal

        Returns:
            Dictionary of audio statistics
        """
        return {
            'rms': float(np.sqrt(np.mean(audio ** 2))),
            'peak': float(np.max(np.abs(audio))),
            'mean': float(np.mean(audio)),
            'std': float(np.std(audio)),
            'clipping_percent': self.detect_clipping(audio),
            'duration_seconds': len(audio) / self.sample_rate
        }