import os
import time
import tempfile
import threading
import requests
import speech_recognition as sr
from config import Config
from core.tts_engine import TTSEngine

WHISPER_CONTEXT_PROMPT = (
    "Sahayak, MyGov, mygov.in, Aadhaar, UIDAI, Voter ID, DigiLocker, PAN card, "
    "Passport Seva, EPFO, Parivahan, IRCTC, open website, search, kholo, update, "
    "mobile number change, Hindi, Hinglish, English Indian command"
)

class ContinuousVoiceListenerWorker:
    """
    Continuous background worker thread supporting stateful conversational mode:
    1. Mutes microphone during TTS audio playback (TTSEngine.is_speaking) to prevent self-talk loops.
    2. IDLE: Listens for wake-word 'Sahayak' (सहायक).
    3. ACTIVE SESSION: Once activated, continues listening and responding to EVERY user sentence
       without requiring 'Sahayak' repeatedly.
    4. STOP: When user says 'Sahayak stop' or 'stop', switches back to IDLE.
    """
    def __init__(self, on_command_detected, on_stop_command, on_listening_state_change, on_error=None):
        self.on_command_detected = on_command_detected
        self.on_stop_command = on_stop_command
        self.on_listening_state_change = on_listening_state_change
        self.on_error = on_error
        self.is_running = False
        self.in_active_session = False
        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = 1000  # Higher threshold to filter ambient room noise
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.6
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self._thread = None


    def start(self):
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.is_running = False
        self.in_active_session = False

    def _listen_loop(self):
        print("[ContinuousVoiceListener] Active & Listening for Wake-Word 'Sahayak'...")
        
        # Calibrate ambient noise level ONCE on initialization
        try:
            with sr.Microphone() as init_source:
                self.recognizer.adjust_for_ambient_noise(init_source, duration=0.5)
        except Exception as e_cal:
            print(f"[ContinuousVoiceListener Warning] Noise calibration warning: {e_cal}")

        # Noise, phantom audio hallucinations & filler word filter list
        NOISE_FILLER_WORDS = {
            "um", "uh", "er", "ah", "my", "ir", "the", "a", "oh", "open my",
            "thank you", "thanks", "thank you so much", "thanks a lot", "thankyou",
            "sihango", "shango", "you're welcome", "welcome"
        }


        while self.is_running:
            try:
                # Mute mic brief moment while agent TTS is actively generating or playing audio
                if TTSEngine.is_speaking:
                    time.sleep(0.1)
                    continue

                state_msg = "⚡ Active Conversation (Listening...)" if self.in_active_session else "🟢 Say 'Sahayak'..."
                if self.on_listening_state_change:
                    self.on_listening_state_change(state_msg)

                with sr.Microphone() as source:
                    try:
                        audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=8)
                    except sr.WaitTimeoutError:
                        continue

                # Check again if TTS started speaking during audio capture
                if TTSEngine.is_speaking or not self.is_running:
                    continue

                if self.on_listening_state_change:
                    self.on_listening_state_change("Processing speech...")

                transcript = self._transcribe_audio(audio)
                clean_text = transcript.strip().lower() if transcript else ""
                
                # Filter background noise fragments, filler words, or ultra-short sound clips
                if not transcript or len(clean_text) < 3 or clean_text in NOISE_FILLER_WORDS:
                    continue


                print(f"[ContinuousVoiceListener] Heard: '{transcript}' (Active Mode: {self.in_active_session})")
                lower_text = transcript.lower().strip()

                # Check STOP triggers (strictly require wake-word 'sahayak stop' or standalone stop words)
                explicit_stop_phrases = ["sahayak stop", "stop sahayak", "ruk jao sahayak", "sahayak ruko", "sahayak bas karo", "bye sahayak", "exit sahayak"]
                standalone_stop_words = ["stop", "ruko", "ruk jao", "bas karo", "bye"]

                is_stop = (lower_text in standalone_stop_words) or any(phrase in lower_text for phrase in explicit_stop_phrases)

                if is_stop:
                    print("[ContinuousVoiceListener] 🛑 STOP command detected! Stopping speech & returning to Standby IDLE mode.")
                    TTSEngine.stop()
                    self.in_active_session = False
                    if self.on_stop_command:
                        self.on_stop_command(transcript)
                    time.sleep(0.5)
                    continue



                wake_words = ["sahayak", "सहायक", "sahayaka", "sahayk", "shayak", "sahyak", "saayak", "sahaayak"]
                has_wake_word = any(w in lower_text for w in wake_words)

                if self.in_active_session:
                    # Already in active conversation: ANY user input is processed
                    command_text = self._clean_transcript(transcript)
                    print(f"[ContinuousVoiceListener] 🗣️ Active Conversation Command: '{command_text}'")
                    if self.on_command_detected:
                        self.on_command_detected(transcript, command_text)
                    time.sleep(1.5)

                elif has_wake_word:
                    # Wake word detected: Enter Active Session!
                    self.in_active_session = True
                    command_text = self._extract_command(transcript)
                    print(f"[ContinuousVoiceListener] ⚡ Wake Word Triggered! Session ACTIVE. Command: '{command_text}'")
                    if self.on_command_detected:
                        self.on_command_detected(transcript, command_text)
                    time.sleep(1.5)

            except Exception as e:
                print(f"[ContinuousVoiceListener Exception] {e}")
                time.sleep(1.0)

    def _clean_transcript(self, transcript: str) -> str:
        """Cleans wake word prefixes if user repeated it in active mode."""
        lower = transcript.lower()
        wake_words = ["sahayak", "सहायक", "sahayaka", "sahayk", "shayak", "sahyak", "saayak", "sahaayak"]
        for w in wake_words:
            if lower.startswith(w):
                return transcript[len(w):].strip(" ,:.-")
        return transcript.strip()

    def _extract_command(self, transcript: str) -> str:
        """Extracts the command text after removing the 'Sahayak' wake word prefix/suffix."""
        lower = transcript.lower()
        wake_words = ["sahayak", "सहायक", "sahayaka", "sahayk", "shayak", "sahyak", "saayak", "sahaayak"]
        
        target_word = ""
        target_idx = -1
        for w in wake_words:
            idx = lower.find(w)
            if idx != -1 and (target_idx == -1 or idx < target_idx):
                target_idx = idx
                target_word = w

        if target_idx != -1:
            after_text = transcript[target_idx + len(target_word):].strip(" ,:.-")
            if len(after_text) > 1:
                return after_text
            
            before_text = transcript[:target_idx].strip(" ,:.-")
            if len(before_text) > 1:
                return before_text

        return "Hello Sahayak"

    def _transcribe_audio(self, audio) -> str:
        """Multi-Engine Speech-to-Text Pipeline: Google STT (High Accuracy & 0 Rate Limit) -> Groq Whisper API."""
        transcript = ""

        # Engine 1: Google Speech Recognition (High Accuracy for Hindi/English, 0 Rate Limits)
        try:
            try:
                transcript = self.recognizer.recognize_google(audio, language="en-IN")
            except sr.UnknownValueError:
                transcript = self.recognizer.recognize_google(audio, language="hi-IN")
        except Exception:
            pass

        # Engine 2: Groq Whisper API Fallback
        if not transcript:
            api_key = Config.get_api_key()
            if api_key:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_filename = tmp_file.name
                        tmp_file.write(audio.get_wav_data())

                    url = "https://api.groq.com/openai/v1/audio/transcriptions"
                    headers = {"Authorization": f"Bearer {api_key}"}
                    
                    with open(tmp_filename, "rb") as file_obj:
                        files = {"file": ("audio.wav", file_obj, "audio/wav")}
                        data = {
                            "model": Config.GROQ_WHISPER_MODEL,
                            "prompt": WHISPER_CONTEXT_PROMPT,
                            "temperature": 0.0
                        }
                        response = requests.post(url, headers=headers, files=files, data=data, timeout=8)
                    
                    os.remove(tmp_filename)

                    if response.status_code == 200:
                        transcript = response.json().get("text", "").strip()
                except Exception as e:
                    print(f"[ContinuousVoiceListener] Groq Whisper error: {e}")

        return transcript


class VoiceListenerWorker:
    """Single-shot microphone worker for manual mic button click."""
    def __init__(self, on_success, on_error, on_start):
        self.on_success = on_success
        self.on_error = on_error
        self.on_start = on_start
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        try:
            if self.on_start:
                self.on_start()

            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=12)

            transcript = ""
            try:
                try:
                    transcript = self.recognizer.recognize_google(audio, language="en-IN")
                except sr.UnknownValueError:
                    transcript = self.recognizer.recognize_google(audio, language="hi-IN")
            except Exception:
                pass

            if not transcript:
                api_key = Config.get_api_key()
                if api_key:
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                            tmp_filename = tmp_file.name
                            tmp_file.write(audio.get_wav_data())

                        url = "https://api.groq.com/openai/v1/audio/transcriptions"
                        headers = {"Authorization": f"Bearer {api_key}"}
                        
                        with open(tmp_filename, "rb") as file_obj:
                            files = {"file": ("audio.wav", file_obj, "audio/wav")}
                            data = {
                                "model": Config.GROQ_WHISPER_MODEL,
                                "prompt": WHISPER_CONTEXT_PROMPT,
                                "temperature": 0.0
                            }
                            response = requests.post(url, headers=headers, files=files, data=data, timeout=12)
                        
                        os.remove(tmp_filename)

                        if response.status_code == 200:
                            transcript = response.json().get("text", "").strip()
                    except Exception as e:
                        print(f"[VoiceListenerWorker] Groq Whisper error: {e}")

            if transcript:
                if self.on_success:
                    self.on_success(transcript)
            else:
                if self.on_error:
                    self.on_error("Aapki aawaaz samajh nahi aayi. Kripya fir se bolein.")

        except sr.WaitTimeoutError:
            if self.on_error:
                self.on_error("Aapne kuch nahi bola. Mic timeout ho gaya.")
        except Exception as ex:
            if self.on_error:
                self.on_error(f"Microphone Error: {str(ex)}")
