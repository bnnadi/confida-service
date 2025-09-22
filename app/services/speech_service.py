import speech_recognition as sr
from pydub import AudioSegment
import io
from app.exceptions import AIServiceError

class SpeechToTextService:
    def __init__(self):
        try:
            self.recognizer = sr.Recognizer()
            # Configure recognizer settings
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
        except Exception as e:
            raise AIServiceError(f"Failed to initialize speech recognition: {e}")
    
    def transcribe_audio(self, audio_data: bytes, language: str = "en-US") -> str:
        """Transcribe audio with better error handling and language support."""
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to WAV format
            wav_data = io.BytesIO()
            audio.export(wav_data, format="wav")
            wav_data.seek(0)
            
            with sr.AudioFile(wav_data) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio, language=language)
                return text
        except sr.UnknownValueError:
            raise AIServiceError("Could not understand audio")
        except sr.RequestError as e:
            raise AIServiceError(f"Speech recognition service error: {e}")
        except Exception as e:
            raise AIServiceError(f"Transcription failed: {str(e)}")
