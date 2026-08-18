from typing import Dict, Any, Tuple
from browser_agent.models import AgentAction, ActionType, SafetyLevel

class SafetyManager:
    """Enforces security policy, action permissions, and user confirmation gates."""

    CONFIRMATION_KEYWORDS = [
        "pay", "payment", "buy", "purchase", "book ticket", "book train",
        "confirm booking", "checkout", "submit form", "delete", "remove account",
        "transfer", "otp", "password", "credit card", "debit card"
    ]

    BLOCKED_DOMAINS = [
        "malware.testing", "phishing.test"
    ]

    @classmethod
    def evaluate_action_safety(cls, action: AgentAction, current_url: str) -> Tuple[SafetyLevel, str]:
        """Evaluates whether an action can run automatically, requires user confirmation, or is blocked."""
        
        # 1. Check URL domain restrictions
        for blocked in cls.BLOCKED_DOMAINS:
            if blocked in current_url.lower():
                return SafetyLevel.BLOCKED, f"Domain '{blocked}' is blocked by security policy."

        # 2. Check for confirmation-requiring actions
        if action.action == ActionType.CLICK:
            target_text = ((action.reason or "") + " " + (action.target_selector or "")).lower()
            for kw in cls.CONFIRMATION_KEYWORDS:
                if kw in target_text:
                    return SafetyLevel.CONFIRM_REQUIRED, f"Action matches safety keyword '{kw}'. User confirmation is required before proceeding."

        # 3. Check for ASK_USER action type
        if action.action == ActionType.ASK_USER:
            return SafetyLevel.CONFIRM_REQUIRED, "Action requires user input."

        return SafetyLevel.SAFE, "Action is permitted."
