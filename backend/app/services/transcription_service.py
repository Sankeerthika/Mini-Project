import os
from dotenv import load_dotenv

load_dotenv()

import whisper


class TranscriptionError(Exception):
    pass


class TranscriptionService:
    def __init__(self, model_name: str | None = None):
        if model_name is None:
            model_name = os.getenv("WHISPER_MODEL", "base")
        valid = {"tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3", "turbo"}
        if model_name not in valid:
            raise TranscriptionError(
                f"Invalid WHISPER_MODEL value {model_name!r}. "
                f"Allowed: {', '.join(sorted(valid))}"
            )
        self.model_name = model_name
        self.model = None
        self.transcribe_call_count = 0

    def _load_model(self):
        if self.model is None:
            print(f"[TranscriptionService] Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            print(f"[TranscriptionService] Whisper model '{self.model_name}' loaded successfully.")
        return self.model

    def transcribe_audio(self, audio_path: str) -> str:
        if not audio_path:
            raise FileNotFoundError("Audio path is empty")
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Recording file not found: {os.path.basename(audio_path)}")

        model = self._load_model()
        try:
            result = model.transcribe(audio_path)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}") from e

        self.transcribe_call_count += 1
        text = result.get("text", "") if isinstance(result, dict) else ""
        return (text or "").strip()


_default_service: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    global _default_service
    if _default_service is None:
        _default_service = TranscriptionService()
    return _default_service
