class BrowserAgentError(Exception):
    """Base exception for Sahayak Browser Agent."""
    pass

class ActionValidationError(BrowserAgentError):
    """Raised when an agent action is invalid or unsafe."""
    pass

class SafetyConfirmationRequired(BrowserAgentError):
    """Raised when an action requires explicit user confirmation."""
    def __init__(self, message: str, action_details: dict):
        super().__init__(message)
        self.action_details = action_details

class TargetNotFoundError(BrowserAgentError):
    """Raised when target element cannot be found on page."""
    pass

class AmbiguousTargetError(BrowserAgentError):
    """Raised when target element matches multiple candidates."""
    pass

class CaptchaDetectedError(BrowserAgentError):
    """Raised when CAPTCHA is detected on page."""
    pass

class OTPRequiredError(BrowserAgentError):
    """Raised when OTP input is required on page."""
    pass

class TaskTimeoutError(BrowserAgentError):
    """Raised when browser agent task exceeds maximum allowed execution time."""
    pass

class ActionLimitExceededError(BrowserAgentError):
    """Raised when task exceeds maximum allowed step actions limit."""
    pass
