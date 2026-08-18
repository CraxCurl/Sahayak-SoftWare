# 🤖 Sahayak (सहायक) - AI Voice & Desktop Floating Assistant

**Sahayak** is a sleek, AI-powered desktop assistant built for Windows and cross-platform desktop operating systems. It lives on your screen as a translucent floating window, listens to your voice commands in Hindi, Hinglish, or English, uses Groq's superfast AI model (`llama-3.3-70b-versatile` & `whisper-large-v3-turbo`), and automatically performs actions like opening government portals (`mygov.in`, Aadhaar phone update, ECI Voter portal, etc.), launching web searches, and opening local applications.

---

## ✨ Features

- 🖥️ **Lives On Your Screen**: Frameless, translucent dark-glass overlay widget that stays on top and can be dragged anywhere on your desktop.
- 🎙️ **Voice & Text Control**: Click **🎙️ Speak** to record your voice command or type into the fallback text box.
- 🗣️ **Multilingual Indian Accent AI**: Powered by Groq Whisper & Llama 3.3 for Hindi, Hinglish, and English voice commands.
- ⚡ **Automated Action Execution**:
  - Open Indian government portals: `mygov.in`, UIDAI Aadhaar update portal (`myaadhaar.uidai.gov.in`), Voter Services, DigiLocker, PAN Card, Passport Seva, EPFO, IRCTC, etc.
  - Open custom websites in default web browser.
  - Perform web searches on Google.
  - Launch desktop applications (Notepad, Calculator, Command Prompt, Chrome).
- ⚙️ **In-App API Key Setup**: Easily configure your `GROQ_API_KEY` via the built-in Settings dialog or `.env` file.

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.10 or higher installed.
- Working Microphone (for voice commands).

### 2. Install Dependencies
Open terminal or PowerShell in the `Sahayak-SoftWare` directory:

```bash
pip install -r requirements.txt
```

> **Note for PyAudio on Windows**: If `pip install PyAudio` fails, install PyAudio wheels directly using `pip install pyaudio`.

### 3. Set Up Groq API Key
1. Get a free API Key from [console.groq.com](https://console.groq.com).
2. Option A: Create a `.env` file in the project folder with:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. Option B: Simply run the application and click the **⚙️ Settings** icon in the Sahayak title bar to enter your key directly.

### 4. Run Sahayak

```bash
python main.py
```

---

## 🗣️ Example Voice & Text Commands

Try saying or typing any of the following:

- **Opening MyGov Portal**:
  - *"MyGov site open karo"*
  - *"Open mygov.in in Chrome"*

- **Updating Aadhaar Phone Number**:
  - *"Aadhaar card phone number change karne ki site kholo"*
  - *"Open UIDAI portal"*

- **Voter ID Services**:
  - *"Voter ID apply karne wala form khol do"*

- **DigiLocker / Document Services**:
  - *"DigiLocker khol do"*

- **General Web Search**:
  - *"Dhoondo latest government schemes for farmers"*

- **Desktop Utilities**:
  - *"Open Notepad"*
  - *"Calculator kholo"*

---

## 📁 Project Architecture

```
Sahayak-SoftWare/
├── main.py                  # App entry point
├── config.py                # App configuration & .env management
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── README.md                # Documentation
├── core/
│   ├── ai_engine.py         # Groq LLM & function call intent parsing
│   └── speech_handler.py    # Threaded audio recording & STT engine
├── actions/
│   ├── action_runner.py     # Executes web browser & desktop actions
│   └── portal_registry.py   # Mappings for Indian Gov & Utility portals
└── ui/
    ├── overlay_widget.py    # Floating PyQt6 glassmorphism window
    ├── settings_dialog.py   # Settings modal for API keys
    └── styles.py            # Dark theme QSS styling
```
