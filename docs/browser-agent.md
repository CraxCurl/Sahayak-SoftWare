# Sahayak Playwright Browser Agent Guide

## 1. Features

- **Autonomous Iterative Execution**: Runs `OBSERVE -> UNDERSTAND -> PLAN -> DECIDE -> ACT -> VERIFY -> OBSERVE AGAIN` loop.
- **Playwright Integration**: High-performance browser automation using Chromium in an isolated context.
- **Language & Popup Intelligence**: Automatically detects IRCTC language selection popups, cookie consent banners, login modals, CAPTCHAs, and OTP requests.
- **Interactive User Decision Cards**: Asks user for decisions whenever meaningful choices or confirmation are required (`ASK_USER`).
- **Safety Policy Engine**: Requires explicit user confirmation before executing financial transactions, payments, or sensitive form submissions.
- **Multi-Tab Support**: Track, switch, and close multiple open browser tabs.
- **Adaptive Screenshots**: Captures screenshots adaptively during modals, initial page loads, or DOM ambiguity to minimize latency and API cost.

---

## 2. Supported Actions

- `NAVIGATE`: Navigate to target URL
- `CLICK`: Click interactive DOM element
- `TYPE`: Fill text into input fields
- `SELECT`: Select option from dropdown
- `SCROLL`: Scroll page up or down
- `PRESS_KEY`: Press keyboard key (Enter, Tab, Space, Escape)
- `WAIT`: Pause briefly for dynamic content
- `GO_BACK`: Navigate back in history
- `SWITCH_TAB`: Switch active browser tab
- `ASK_USER`: Prompt user for decision or choice
- `DONE`: Task completed
- `FAIL`: Task failed
