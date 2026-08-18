# Sahayak Architecture & Intelligent Browser Agent Specification

## 1. System Overview

Sahayak (सहायक) is a desktop AI voice & web automation assistant designed to execute complex, multi-step natural language instructions across desktop applications and web portals.

```text
                    USER
                      |
                      v
              +---------------+
              |    SAHAYAK     |
              | Chat / Voice   |
              +-------+-------+
                      |
                      v
              +---------------+
              | TASK PLANNER  |
              |     / LLM     |
              +-------+-------+
                      |
                      v
              +---------------+
              | BROWSER AGENT |
              +-------+-------+
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
        DOM      Accessibility  Screenshot
                    Tree
          |           |           |
          +-----------+-----------+
                      |
                      v
              PAGE UNDERSTANDING
                      |
                      v
                 AI REASONER
                      |
             +--------+--------+
             |                 |
             v                 v
          ACTION          ASK USER
             |                 |
             v                 |
        ACTION ENGINE <--------+
             |
             v
          BROWSER
             |
             v
          WEBSITE
```

---

## 2. Core Modules Architecture

### `browser_agent/`
- **`browser_manager.py`**: Manages Playwright Chromium lifecycle, multi-tab switching, isolated browser profiles, and crash recovery.
- **`dom_extractor.py`**: Extracts visible, interactive elements (`button`, `a`, `input`, `select`, `textarea`, `role="button"`) and assigns stable IDs (`e-1`, `e-2`).
- **`accessibility.py`**: Obtains accessibility tree snapshots for semantic reasoning over dialogs and buttons.
- **`screenshot.py`**: Adaptive screenshot engine capturing visual state during initial load, popup/modal detection, or DOM ambiguity.
- **`popup_detector.py`**: Detects language selection popups, cookie consent banners, login modals, CAPTCHAs, and OTP input requests.
- **`action_validator.py`**: Validates action targets, target visibility, enabled state, target non-ambiguity, and safety policies.
- **`action_executor.py`**: Executes Playwright browser actions (`NAVIGATE`, `CLICK`, `TYPE`, `SELECT`, `SCROLL`, `PRESS_KEY`, `WAIT`, `GO_BACK`, `SWITCH_TAB`, `CLOSE_TAB`, `ASK_USER`, `DONE`, `FAIL`).
- **`safety_manager.py`**: Enforces user confirmation gates for payments, bookings, account settings, and sensitive transactions.
- **`agent_loop.py`**: Main iterative engine running `OBSERVE -> UNDERSTAND -> PLAN -> DECIDE -> ACT -> VERIFY -> OBSERVE AGAIN`.
- **`state_manager.py`**: Tracks task model state transitions and emits real-time agent events (`TASK_STARTED`, `POPUP_DETECTED`, `USER_INPUT_REQUIRED`, etc.).
- **`memory_manager.py`**: Stores user explicit preferences (e.g. IRCTC preferred language = English) with explicit consent.
