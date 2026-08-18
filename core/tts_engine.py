import os
import time
import tempfile
import threading
import asyncio
import re
import pygame
import edge_tts
from gtts import gTTS

# Microsoft Azure Deep Male Neural HD Voice Mapping for Indian Languages & English
NEURAL_VOICES = {
    "hi": "hi-IN-MadhurNeural",       # Deep Male Hindi (Warm & Natural)
    "en": "en-IN-PrabhatNeural",      # Deep Male English (Indian Accent)
    "ta": "ta-IN-ValluvarNeural",     # Deep Male Tamil
    "te": "te-IN-MohanNeural",        # Deep Male Telugu
    "bn": "bn-IN-BashkarNeural",      # Deep Male Bengali
    "gu": "gu-IN-NiranjanNeural",     # Deep Male Gujarati
    "mr": "mr-IN-ManoharNeural",      # Deep Male Marathi
    "kn": "kn-IN-GaganNeural",        # Deep Male Kannada
    "ml": "ml-IN-MidhunNeural",       # Deep Male Malayalam
    "pa": "pa-IN-GurpreetNeural"      # Deep Male Punjabi
}

def detect_language_code(text: str) -> str:
    """Detects primary language code from unicode script ranges."""
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "ta"
    elif re.search(r'[\u0C00-\u0C7F]', text):
        return "te"
    elif re.search(r'[\u0980-\u09FF]', text):
        return "bn"
    elif re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"
    elif re.search(r'[\u0C80-\u0CFF]', text):
        return "kn"
    elif re.search(r'[\u0D00-\u0D7F]', text):
        return "ml"
    elif re.search(r'[\u0A00-\u0A7F]', text):
        return "pa"
    elif re.search(r'[\u0900-\u097F]', text):
        return "hi"
    else:
        return "en"

class TTSEngine:
    _pygame_initialized = False
    is_speaking = False
    _current_speech_id = 0
    _lock = threading.Lock()

    @classmethod
    def _init_pygame(cls):
        if not cls._pygame_initialized:
            try:
                pygame.mixer.init()
                cls._pygame_initialized = True
            except Exception as e:
                print(f"[TTSEngine Error] Failed to init pygame mixer: {e}")

    @classmethod
    def speak_async(cls, text: str):
        """
        Speaks text out loud asynchronously using Microsoft Edge Neural HD Voice.
        Allows immediate interruption if new speech or stop() is requested.
        """
        if not text or not text.strip():
            return
        
        # Stop any previous playback immediately
        cls.stop()
        
        with cls._lock:
            cls._current_speech_id += 1
            speech_id = cls._current_speech_id

        thread = threading.Thread(target=cls._speak_thread, args=(speech_id, text), daemon=True)
        thread.start()

    @classmethod
    def _speak_thread(cls, speech_id: int, text: str):
        tmp_filename = None
        try:
            cls.is_speaking = True
            cls._init_pygame()
            clean_text = text.strip()
            lang_code = detect_language_code(clean_text)
            voice = NEURAL_VOICES.get(lang_code, "en-IN-PrabhatNeural")

            print(f"[TTSEngine] Speaking with Deep Male Neural Voice '{voice}' ({lang_code}): {clean_text[:40]}...")

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_filename = f.name

            # Generate Deep Male Neural HD Voice via edge-tts with pitch tuning (-5Hz)
            try:
                async def generate():
                    communicate = edge_tts.Communicate(clean_text, voice, pitch="-5Hz", rate="-2%")
                    await communicate.save(tmp_filename)

                asyncio.run(generate())
            except Exception as e_edge:
                print(f"[TTSEngine Warning] Edge TTS failed ({e_edge}), falling back to gTTS")
                tts = gTTS(text=clean_text, lang=lang_code, slow=False)
                tts.save(tmp_filename)

            # Check if this speech task was cancelled / interrupted during audio generation
            if speech_id != cls._current_speech_id:
                print(f"[TTSEngine] Speech #{speech_id} cancelled prior to playback.")
                return

            pygame.mixer.music.load(tmp_filename)
            pygame.mixer.music.play()

            # Wait while audio plays, checking for interruption
            while pygame.mixer.music.get_busy() and speech_id == cls._current_speech_id:
                time.sleep(0.05)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"[TTSEngine Exception] Speech output error: {e}")
        finally:
            if tmp_filename and os.path.exists(tmp_filename):
                try:
                    os.remove(tmp_filename)
                except Exception:
                    pass
            if speech_id == cls._current_speech_id:
                cls.is_speaking = False

    @classmethod
    def stop(cls):
        """Immediately stops all TTS audio playback mid-sentence and cancels active generation."""
        with cls._lock:
            cls._current_speech_id += 1
        cls.is_speaking = False
        try:
            if cls._pygame_initialized and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception as e:
            print(f"[TTSEngine Warning] Stop speech failed: {e}")


