# Sahayak Security & Safety Policy

## 1. Security Architecture

- **Isolated Browser Context**: Sahayak uses an isolated Playwright browser profile by default, preventing unauthorized access to personal Chrome user data.
- **Safety Confirmation Gates**: Purchasing, train booking checkout, financial payments, data deletion, and sensitive settings changes require explicit user confirmation.
- **No CAPTCHA Bypassing**: CAPTCHAs are detected automatically. The agent pauses execution and prompts the user to complete the challenge.
- **Secure OTP Handling**: OTPs are entered via user prompts; secrets are never logged or stored in persistent files.
- **Secret Redaction**: Passwords, API keys, tokens, and cookies are redacted from log outputs.
- **Loop & Execution Limits**: Configurable action step limits (default 50) and timeouts (default 10 mins) prevent infinite loops or runaway processes.
