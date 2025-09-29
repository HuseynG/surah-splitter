"""
Configuration manager for Azure GPT Audio service settings.

This module handles loading, validation, and management of configuration
for the GPT Audio service from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import json
from threading import RLock

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


@dataclass
class GPTAudioConfig:
    """Configuration for GPT Audio service."""

    # Azure GPT Audio endpoints
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    deployment_name: Optional[str] = None
    api_version: str = "2024-10-01-preview"

    # Fallback Azure OpenAI settings
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None

    # API settings
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 2

    # Audio processing settings
    max_audio_size_mb: float = 25.0
    max_audio_duration_seconds: float = 300.0
    supported_audio_formats: list = field(default_factory=lambda: ['wav', 'mp3', 'm4a', 'webm', 'ogg'])
    default_sample_rate: int = 16000
    default_audio_format: str = 'wav'

    # Analysis settings
    default_language: str = 'en'
    enable_audio_feedback: bool = False
    tajweed_strictness: str = 'medium'  # low, medium, high

    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_concurrent_requests: int = 5

    # Logging
    log_level: str = 'INFO'
    log_api_requests: bool = False
    log_api_responses: bool = False

    # Environment
    environment: str = 'development'  # development, staging, production

    # Thread safety
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        with self._lock:
            # Load GPT Audio specific settings
            self.endpoint = os.getenv('GPT_AUDIO_ENDPOINT', os.getenv('ENDPOINT_URL'))
            self.api_key = os.getenv('GPT_AUDIO_API_KEY', os.getenv('AZURE_API_KEY'))
            self.deployment_name = os.getenv('GPT_AUDIO_DEPLOYMENT', os.getenv('DEPLOYMENT_NAME'))

            # Fallback to Azure OpenAI settings
            if not self.endpoint:
                self.azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
                if self.azure_openai_endpoint:
                    # Convert to GPT audio endpoint format if needed
                    if 'openai.azure.com' in self.azure_openai_endpoint:
                        self.endpoint = self.azure_openai_endpoint.replace('https://', 'wss://').rstrip('/') + '/realtime'
                    else:
                        self.endpoint = self.azure_openai_endpoint

            if not self.api_key:
                self.azure_openai_key = os.getenv('AZURE_OPENAI_API_KEY')
                self.api_key = self.azure_openai_key

            if not self.deployment_name:
                self.azure_openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4-realtime-preview')
                self.deployment_name = self.azure_openai_deployment

            # API version
            self.api_version = os.getenv('GPT_AUDIO_API_VERSION', self.api_version)

            # Timeout and retry settings
            self.timeout_seconds = int(os.getenv('GPT_AUDIO_TIMEOUT', '60'))
            self.max_retries = int(os.getenv('GPT_AUDIO_MAX_RETRIES', '3'))
            self.retry_delay_seconds = int(os.getenv('GPT_AUDIO_RETRY_DELAY', '2'))

            # Audio settings
            self.max_audio_size_mb = float(os.getenv('MAX_AUDIO_SIZE_MB', '25.0'))
            self.max_audio_duration_seconds = float(os.getenv('MAX_AUDIO_DURATION', '300.0'))
            self.default_sample_rate = int(os.getenv('DEFAULT_SAMPLE_RATE', '16000'))
            self.default_audio_format = os.getenv('DEFAULT_AUDIO_FORMAT', 'wav')

            # Supported formats
            formats_str = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,webm,ogg')
            self.supported_audio_formats = [f.strip() for f in formats_str.split(',')]

            # Analysis settings
            self.default_language = os.getenv('DEFAULT_ANALYSIS_LANGUAGE', 'en')
            self.enable_audio_feedback = os.getenv('ENABLE_AUDIO_FEEDBACK', 'false').lower() == 'true'
            self.tajweed_strictness = os.getenv('TAJWEED_STRICTNESS', 'medium')

            # Performance settings
            self.enable_caching = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
            self.cache_ttl_seconds = int(os.getenv('CACHE_TTL', '3600'))
            self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))

            # Logging
            self.log_level = os.getenv('LOG_LEVEL', 'INFO')
            self.log_api_requests = os.getenv('LOG_API_REQUESTS', 'false').lower() == 'true'
            self.log_api_responses = os.getenv('LOG_API_RESPONSES', 'false').lower() == 'true'

            # Environment
            self.environment = os.getenv('ENVIRONMENT', os.getenv('APP_ENV', 'development'))

            logger.info(f"GPTAudioConfig loaded for environment: {self.environment}")

    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        with self._lock:
            # Check required fields
            if not self.endpoint:
                logger.error("GPT Audio endpoint not configured")
                return False

            if not self.api_key:
                logger.error("GPT Audio API key not configured")
                return False

            if not self.deployment_name:
                logger.error("GPT Audio deployment name not configured")
                return False

            # Validate endpoint format
            if not (self.endpoint.startswith('https://') or self.endpoint.startswith('wss://')):
                logger.error(f"Invalid endpoint format: {self.endpoint}")
                return False

            # Validate other settings
            if self.tajweed_strictness not in ['low', 'medium', 'high']:
                logger.warning(f"Invalid tajweed_strictness: {self.tajweed_strictness}, using 'medium'")
                self.tajweed_strictness = 'medium'

            if self.default_language not in ['en', 'ar']:
                logger.warning(f"Invalid default_language: {self.default_language}, using 'en'")
                self.default_language = 'en'

            return True

    def get_endpoint_url(self) -> str:
        """Get the properly formatted endpoint URL."""
        with self._lock:
            # Ensure proper format for GPT audio
            if self.endpoint:
                # Convert https to wss for realtime if needed
                if '/realtime' in self.endpoint and self.endpoint.startswith('https://'):
                    return self.endpoint.replace('https://', 'wss://')
                return self.endpoint

            return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        with self._lock:
            return {
                'endpoint': self.endpoint,
                'deployment_name': self.deployment_name,
                'api_version': self.api_version,
                'environment': self.environment,
                'timeout_seconds': self.timeout_seconds,
                'max_retries': self.max_retries,
                'max_audio_size_mb': self.max_audio_size_mb,
                'max_audio_duration_seconds': self.max_audio_duration_seconds,
                'supported_audio_formats': self.supported_audio_formats,
                'default_language': self.default_language,
                'enable_audio_feedback': self.enable_audio_feedback,
                'tajweed_strictness': self.tajweed_strictness,
                'enable_caching': self.enable_caching,
                'log_level': self.log_level
            }

    def save_to_file(self, file_path: str) -> None:
        """Save configuration to a JSON file."""
        with self._lock:
            config_dict = self.to_dict()
            # Don't save sensitive data
            config_dict.pop('api_key', None)

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)

            logger.info(f"Configuration saved to {file_path}")

    def load_from_file(self, file_path: str) -> None:
        """Load configuration from a JSON file."""
        with self._lock:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Configuration file not found: {file_path}")
                return

            try:
                with open(path, 'r') as f:
                    config_dict = json.load(f)

                # Update configuration (except sensitive data)
                for key, value in config_dict.items():
                    if hasattr(self, key) and key not in ['api_key', '_lock']:
                        setattr(self, key, value)

                logger.info(f"Configuration loaded from {file_path}")

            except Exception as e:
                logger.error(f"Failed to load configuration from {file_path}: {str(e)}")

    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'api-key': self.api_key or '',
            'Content-Type': 'application/json',
            'User-Agent': f'SurahSplitter/1.0 ({self.environment})'
        }

    def get_timeout_config(self) -> Dict[str, Any]:
        """Get timeout configuration for requests."""
        return {
            'timeout': self.timeout_seconds,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay_seconds
        }

    def update(self, **kwargs) -> None:
        """Update configuration with provided keyword arguments."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key) and key != '_lock':
                    setattr(self, key, value)
                    logger.debug(f"Updated config: {key} = {value}")

    def validate_audio_format(self, audio_format: str) -> bool:
        """Check if an audio format is supported."""
        return audio_format.lower() in self.supported_audio_formats

    def get_cache_key(self, analysis_type: str, audio_hash: str, language: str) -> str:
        """Generate a cache key for analysis results."""
        return f"gpt_audio:{analysis_type}:{audio_hash}:{language}:{self.tajweed_strictness}"


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


# Singleton instance
_config_instance: Optional[GPTAudioConfig] = None
_config_lock = RLock()


def get_config() -> GPTAudioConfig:
    """Get the singleton configuration instance."""
    global _config_instance

    with _config_lock:
        if _config_instance is None:
            _config_instance = GPTAudioConfig()
            _config_instance.load_from_env()

        return _config_instance


def reset_config() -> None:
    """Reset the configuration instance (mainly for testing)."""
    global _config_instance

    with _config_lock:
        _config_instance = None
        logger.debug("Configuration reset")


def validate_environment() -> bool:
    """Validate that all required environment variables are set."""
    required_vars = [
        ('GPT_AUDIO_ENDPOINT', 'ENDPOINT_URL', 'AZURE_OPENAI_ENDPOINT'),
        ('GPT_AUDIO_API_KEY', 'AZURE_API_KEY', 'AZURE_OPENAI_API_KEY'),
        ('GPT_AUDIO_DEPLOYMENT', 'DEPLOYMENT_NAME', 'AZURE_OPENAI_DEPLOYMENT')
    ]

    all_valid = True

    for var_group in required_vars:
        if not any(os.getenv(var) for var in var_group):
            logger.error(f"Missing required environment variable. Set one of: {', '.join(var_group)}")
            all_valid = False

    if all_valid:
        logger.info("Environment validation successful")
    else:
        logger.error("Environment validation failed")

    return all_valid