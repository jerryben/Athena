"""Voice transcription service for Athena."""

import os
import tempfile
from typing import Any, Dict

import httpx
from loguru import logger

try:
    import whisper
    WHISPER_AVAILABLE = True
    logger.info("openai-whisper available")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("openai-whisper not installed, will use Ollama transcription")


class TranscriptionService:
    """Service for transcribing audio to text."""

    def __init__(self):
        self.whisper_model = None
        if WHISPER_AVAILABLE:
            self._load_whisper()

    def _load_whisper(self):
        """Load Whisper model."""
        try:
            logger.info("Loading Whisper base model...")
            self.whisper_model = whisper.load_model("base")
            logger.success("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            self.whisper_model = None

    def transcribe_audio(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """Transcribe audio bytes to text."""
        if self.whisper_model:
            return self._transcribe_with_whisper(audio_data, language)
        else:
            return self._transcribe_with_ollama(audio_data, language)

    def _transcribe_with_whisper(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Transcribe using local Whisper model."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            try:
                result = self.whisper_model.transcribe(
                    tmp_path,
                    language=language,
                    verbose=False
                )
                return {
                    "text": result.get("text", "").strip(),
                    "language": result.get("language", language),
                }
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return {"error": str(e)}

    def _transcribe_with_ollama(self, audio_data: bytes, language: str) -> Dict[str, Any]:
        """Transcribe using Ollama's whisper model."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            try:
                with open(tmp_path, 'rb') as f:
                    response = httpx.post(
                        "http://localhost:11434/api/transcriptions",
                        json={"model": "whisper", "prompt": ""},
                        files={"audio": f},
                        timeout=120
                    )

                if response.status_code == 200:
                    result = response.json()
                    return {"text": result.get("text", "").strip(), "language": language}
                else:
                    return {"error": f"Ollama transcription failed: {response.text}"}
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"Ollama transcription failed: {e}")
            return {"error": str(e)}

    def transcribe_file(self, file_path: str, language: str = "en") -> Dict[str, Any]:
        """Transcribe an audio file."""
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            return self.transcribe_audio(audio_data, language)
        except Exception as e:
            return {"error": str(e)}


# Global instance
transcription_service = TranscriptionService()
