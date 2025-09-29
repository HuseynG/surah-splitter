# Surah Splitter (Service-Based Architecture)

This is the service-based implementation of the Surah Splitter project, designed to enhance modularity, support direct service access, and improve maintainability.

## 🚀 Quick Start with Docker

### Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (included with Docker Desktop)
- 4GB+ available RAM

### 1. Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd surah-splitter

# Create .env file with your Azure OpenAI credentials
# (See Environment Configuration section below)
```

### 2. Start the Application

#### Using Make (Recommended)
```bash
# Start the application
make up

# View available commands
make help
```

#### Using Docker Compose directly
```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Demo Interface**: http://localhost:8001/demo
- **Health Check**: http://localhost:8001/health

## 🛠️ Common Commands

### Quick Reference

```bash
# Start the application
make up
# OR
docker-compose up -d

# Stop the application
make down
# OR
docker-compose down

# View logs
make logs
# OR
docker-compose logs -f

# Rebuild and restart
make rebuild
# OR
docker-compose up -d --build

# Open shell in container
make shell
# OR
docker-compose exec surah-splitter /bin/bash

# Check health status
make health

# Run tests
make test
```

### Available Make Commands

| Command | Description |
|---------|-------------|
| `make up` | Start the application |
| `make down` | Stop the application |
| `make restart` | Restart the application |
| `make build` | Build Docker image |
| `make rebuild` | Rebuild and start |
| `make logs` | View logs |
| `make shell` | Open container shell |
| `make status` | Show container status |
| `make health` | Check health status |
| `make clean` | Remove everything |
| `make test` | Run tests |
| `make lint` | Run linting |
| `make format` | Format code |

## 🚢 Deployment Features

- **Auto-restart**: Service automatically restarts on failure
- **Health monitoring**: Regular health checks every 30s
- **Hot-reload**: Code changes are automatically detected
- **Logging**: JSON logging with rotation
- **Persistent data**: Logs, cache, and uploads are preserved

## ⚙️ Environment Configuration

Create a `.env` file with your Azure credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name

# GPT Audio Configuration
GPT_AUDIO_ENDPOINT=https://your-resource.openai.azure.com
GPT_AUDIO_API_KEY=your_key_here
GPT_AUDIO_DEPLOYMENT=gpt-audio
GPT_AUDIO_API_VERSION=2024-10-01-preview
```

## 🔧 Health Monitoring

```bash
# Check health status
make health

# Detailed health information
curl http://localhost:8001/health
```

## 🐛 Troubleshooting

### Common Issues

**Port already in use:**
```bash
lsof -i :8001
# Change port in .env: API_PORT=8002
```

**Container won't start:**
```bash
# Check logs
make logs
# OR
docker-compose logs
```

**Permission errors:**
```bash
# Rebuild without cache
docker-compose build --no-cache
```


## Architecture Overview

The architecture organizes the system into distinct services, each responsible for a specific aspect of the processing pipeline:

1. **TranscriptionService**: Handles audio transcription using WhisperX
2. **AyahMatchingService**: Aligns transcribed words to reference Quranic text
3. **SegmentationService**: Splits audio files based on ayah timestamps
4. **QuranMetadataService**: Manages access to Quranic reference data
5. **PipelineService**: Orchestrates the complete processing pipeline
6. **AzureGPTAudioService**: Advanced AI-powered Tajweed and recitation analysis (NEW)
7. **RealtimeTranscriptionService**: WebSocket-based real-time feedback
8. **PersonalizedLearningService**: Adaptive learning and progress tracking

## 🆕 GPT Audio Features

### Advanced AI-Powered Quranic Analysis

The application now includes cutting-edge GPT Audio capabilities for comprehensive Tajweed analysis and recitation accuracy checking.

#### Feature Comparison

| Feature | Live Transcription | Tajweed Analysis | Recitation Analysis |
|---------|-------------------|------------------|---------------------|
| **Mode** | Real-time streaming | Offline analysis | Offline analysis |
| **Input** | Live audio via WebSocket | Audio file/recording | Audio file + reference text |
| **Output** | Word-by-word feedback | Tajweed scores & issues | Accuracy % & word errors |
| **Language** | Arabic | English/Arabic feedback | English/Arabic feedback |
| **Processing** | ~100ms latency | 2-10 seconds | 2-10 seconds |
| **Use Case** | Practice sessions | Tajweed improvement | Memorization check |

### Tajweed Analysis Features

Comprehensive evaluation of Quranic recitation rules:

- **Makharij (مخارج)**: Points of articulation analysis
- **Sifat (صفات)**: Letter characteristics evaluation
- **Ghunnah (غُنَّة)**: Nasalization duration checking
- **Madd (مَدّ)**: Elongation rules verification
- **Noon Sakinah Rules**: Ikhfa, Idgham, Iqlab, Izhar
- **Qalqalah (قلقلة)**: Echo effect assessment

Each category receives a score from 0-5, with detailed feedback and improvement suggestions.

### Recitation Accuracy Analysis

Compare your recitation against the authentic Quranic text:

- **Accuracy Score**: Overall percentage of correct recitation
- **Missed Words**: Words omitted from the recitation
- **Added Words**: Extra words not in the original text
- **Mispronunciations**: Specific pronunciation errors with timestamps
- **Personalized Feedback**: Tailored suggestions for improvement

### Multi-Language Support

Get feedback in your preferred language:
- **English**: Detailed technical feedback with transliterations
- **Arabic**: Native Arabic feedback with proper RTL formatting

### API Endpoints

```bash
# Tajweed Analysis
POST /api/audio/analyze/tajweed

# Recitation Accuracy
POST /api/audio/analyze/recitation

# Audio Validation
POST /api/audio/analyze/validate

# Service Status
GET /api/audio/analyze/status
```

### Quick Example

```bash
# Analyze Tajweed with English feedback
curl -X POST http://localhost:8001/api/audio/analyze/tajweed \
  -F "audio_file=@recording.wav" \
  -F "language=en" \
  -F "surah_name=Al-Fatiha"

# Check recitation accuracy with Arabic feedback
curl -X POST http://localhost:8001/api/audio/analyze/recitation \
  -F "audio_file=@recording.wav" \
  -F "reference_text=بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ" \
  -F "language=ar"
```

### Demo Interface

Try the new features in the interactive demo:

1. Open http://localhost:8001/demo
2. Select analysis mode: Live / Tajweed / Recitation
3. Choose your preferred language
4. Record or upload audio
5. Get instant AI-powered feedback

## GPT Audio Configuration

Add these environment variables to your `.env` file:

```env
# GPT Audio Configuration (Required for Tajweed/Recitation Analysis)
GPT_AUDIO_ENDPOINT=https://your-resource.openai.azure.com
GPT_AUDIO_API_KEY=your-gpt-audio-api-key
GPT_AUDIO_DEPLOYMENT=gpt-audio-deployment-name
GPT_AUDIO_API_VERSION=2024-10-01-preview

# Audio Processing Settings
MAX_AUDIO_SIZE_MB=25.0           # Maximum audio file size
MAX_AUDIO_DURATION=300.0         # Maximum duration in seconds
DEFAULT_ANALYSIS_LANGUAGE=en     # Default language (en/ar)
ENABLE_AUDIO_FEEDBACK=false      # Enable audio responses
TAJWEED_STRICTNESS=medium         # low/medium/high

# Performance Settings
GPT_AUDIO_TIMEOUT=60             # API timeout in seconds
GPT_AUDIO_MAX_RETRIES=3          # Retry attempts
GPT_AUDIO_MAX_CONCURRENT=5       # Concurrent GPT Audio analysis limit
```

### Azure Setup Requirements

To use GPT Audio features, you need:

1. **Azure OpenAI Resource** with GPT-4 Audio model access
2. **Deployment** of `gpt-4o-audio-preview` or similar
3. **API Key** with appropriate permissions
4. **Network Access** from your deployment environment

See [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/) for setup instructions.



## Original Installation (Non-Docker)
