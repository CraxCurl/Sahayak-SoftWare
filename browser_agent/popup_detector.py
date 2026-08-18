import re
from typing import Dict, Any, List, Optional
from browser_agent.models import DOMElement

class PopupDetector:
    """Detects unexpected UI popups, modals, language selection, cookies, CAPTCHAs, and OTP requests."""

    @classmethod
    def detect_popup(cls, elements: List[DOMElement], modal_text: str, page_title: str) -> Dict[str, Any]:
        # Filter elements belonging to active modals/dialogs if present
        modal_elements = [e for e in elements if e.is_modal_element]
        target_elements = modal_elements if modal_elements else elements

        modal_combined = (modal_text + " " + " ".join([e.text for e in target_elements])).lower()
        full_combined = (modal_text + " " + page_title + " " + " ".join([e.text for e in elements])).lower()

        # 1. Language Selection Popup (e.g., IRCTC, Govt Portals, Demo Modal)
        is_lang_keywords = any(w in modal_combined for w in ["select language", "choose language", "bhasha ka chayan", "pasandida bhasha", "select your language", "language", "bhasha"])
        has_lang_buttons = any(any(w in e.text.lower() for w in ["english", "hindi", "हिन्दी", "tamil"]) for e in target_elements)
        
        if is_lang_keywords or has_lang_buttons:
            options = []
            for el in target_elements:
                t_lower = el.text.lower()
                if any(w in t_lower for w in ["english", "hindi", "हिन्दी", "tamil", "telugu", "kannada", "marathi"]):
                    options.append({"label": el.text or "Language", "value": el.text.lower(), "target_id": el.id})
            
            if not options:
                options = [{"label": "Hindi", "value": "hindi"}, {"label": "English", "value": "english"}]

            return {
                "detected": True,
                "type": "language_selection",
                "title": "Language Selection Popup",
                "question": "The website is asking you to select a language. Which language should I choose?",
                "requires_user": True,
                "options": options
            }

        # 2. CAPTCHA Detection
        if any(w in full_combined for w in ["captcha", "recaptcha", "hcaptcha", "turnstile", "cf-challenge", "robot"]):
            return {
                "detected": True,
                "type": "captcha",
                "title": "CAPTCHA Detected",
                "question": "A CAPTCHA is required to continue. Please solve it in the browser window, then I will continue.",
                "requires_user": True,
                "options": [{"label": "I completed CAPTCHA", "value": "done"}]
            }

        # 3. OTP Detection
        if any(w in full_combined for w in ["enter otp", "verification code", "one time password", "otp sent"]):
            return {
                "detected": True,
                "type": "otp",
                "title": "OTP Input Required",
                "question": "An OTP is required to proceed. Please enter the OTP you received.",
                "requires_user": True,
                "options": []
            }




        # 4. Cookie Consent Banner
        if any(w in combined_text for w in ["cookie", "cookies consent", "accept all cookies", "privacy choices"]):
            accept_elem = None
            for el in elements:
                if any(w in el.text.lower() for w in ["accept", "agree", "allow"]):
                    accept_elem = el
                    break

            return {
                "detected": True,
                "type": "cookie_banner",
                "title": "Cookie Banner Detected",
                "question": None,  # Auto-handled safely by agent
                "requires_user": False,
                "auto_target_id": accept_elem.id if accept_elem else None,
                "options": []
            }

        # 5. Login / Account Required Popup
        if any(w in combined_text for w in ["sign in to continue", "login required", "please login"]):
            return {
                "detected": True,
                "type": "login_required",
                "title": "Login Required",
                "question": "This page requires login. Would you like to log in now?",
                "requires_user": True,
                "options": [{"label": "I logged in", "value": "logged_in"}, {"label": "Cancel", "value": "cancel"}]
            }

        return {
            "detected": False,
            "type": "none",
            "title": "",
            "question": None,
            "requires_user": False,
            "options": []
        }
