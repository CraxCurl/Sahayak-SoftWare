# Sahayak Setup & Execution Guide

## 1. Installation

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## 2. Environment Setup

Create `.env` file from `.env.example`:

```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
HEADLESS=false
MAX_ACTIONS=50
TASK_TIMEOUT=600
```

## 3. Running Sahayak Voice & Browser Assistant

```powershell
python main.py
```

## 4. Running Local Demo Server & Tests

Start Local Demo Server:
```powershell
python demo_server.py
```

Run Sahayak Browser Agent Test Suite:
```powershell
python tests/test_browser_agent.py
```
or
```powershell
pytest tests/test_browser_agent.py
```
