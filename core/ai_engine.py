import json
import re
import time
import requests
from config import Config
from actions.portal_registry import PORTALS

SYSTEM_PROMPT = f"""You are Sahayak (सहायक), an intelligent, context-aware multilingual AI desktop assistant living on the user's screen.

CRITICAL RULES FOR CONTEXT RETENTION, ACTION SUGGESTIONS & FORM FILLING:
1. LONG-TERM CONTEXT RETENTION: Always inspect the full conversation history. Remember what website/portal is currently open (e.g. MyGov, IRCTC, Aadhaar, YouTube) and what the user has asked so far.
2. PROACTIVE WEBPAGE ACTION SUGGESTIONS: When on a webpage (e.g., MyGov, IRCTC) or when the user gives follow-up commands like "login", "participate", "little down", "what options are there":
   - Inspect active site context and suggest 2-3 relevant next actions!
   - Example (MyGov): "MyGov portal open hai. Yahan Login, Mural Design Contest, and Citizen Quiz options hain. Login karein ya Contest check karein?"
   - Example (IRCTC): "IRCTC open hai. Train search karein ya PNR status check karein?"
3. PROACTIVE FORM INPUT PROMPTS: When a user wants to fill out a form or perform a search (e.g. train ticket search, login form, registration):
   - Ask the user for the necessary input fields over voice!
   - Example: "Train search karne ke liye: Kripya 'From Station' aur 'To Station' bataiye."
   - Example: "Login ke liye: Kripya apna Mobile number ya Email bataiye."
4. NO UNNECESSARY CONFIRMATIONS ON URLS: When user specifies a URL/portal to open, execute immediately.
5. CONCISE SPOKEN RESPONSES: Keep your spoken 'reply' clear and brief (1-2 sentences max).
6. Always respond in the EXACT same language used by the user (Hindi, Hinglish, English, etc.).
7. Return ONLY a valid JSON object.

JSON FORMAT SCHEMA:
{{
  "reply": "Clear response with action suggestion or form prompt if needed",
  "action": {{
    "type": "open_url" | "open_portal" | "guided_flow" | "scroll" | "press_key" | "type_input" | "navigate_browser" | "click_screen" | "search_web" | "open_app" | "browser_agent" | "none",
    "params": {{ ... }}
  }}
}}

AVAILABLE PORTALS MATCHING KEYWORDS:
{json.dumps({k: v['keywords'] for k, v in PORTALS.items()}, indent=2)}
"""


class AIEngine:
    def __init__(self):
        self.history = []

    def reset_history(self):
        self.history = []

    def _record_history(self, user_text: str, result: dict):
        """Records user prompt and assistant response into conversation history, maintaining 20-turn context."""
        try:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": json.dumps(result)})
            self.history = self.history[-20:]  # Retain last 20 turns for rich context memory
        except Exception:
            pass

    def process_query(self, user_text: str) -> dict:
        """
        Processes user query with long-term context retention, action suggestions, and form prompts.
        """
        # Fast Heuristic 1: Check for explicit website domains (e.g., vit.ac.in, cc.vit.ac.in, youtube.com)
        domain_match = re.search(r'\b([a-zA-Z0-9-]+\.(?:com|in|ac\.in|org|net|edu|gov\.in|io|co))\b', user_text.lower())
        if domain_match:
            domain = domain_match.group(1)
            full_match = re.search(r'\b([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.(?:ac\.in|gov\.in|co\.in))\b', user_text.lower())
            if full_match:
                domain = full_match.group(1)

            target_url = f"https://{domain}"
            res = {
                "reply": f"Opening {domain}.",
                "action": {"type": "open_url", "params": {"url": target_url}}
            }
            self._record_history(user_text, res)
            return res

        # Fast Heuristic 2: Check portal keywords & web shortcuts
        heuristic_res = self._check_heuristics(user_text)
        if heuristic_res:
            self._record_history(user_text, heuristic_res)
            return heuristic_res

        api_key = Config.get_api_key()
        if not api_key:
            res = {
                "reply": "Groq API Key missing. Add GROQ_API_KEY in Settings.",
                "action": {"type": "none", "params": {}}
            }
            self._record_history(user_text, res)
            return res

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for hist in self.history[-12:]:  # Pass last 12 turns of rich context memory to LLM
            messages.append(hist)
        messages.append({"role": "user", "content": user_text})

        last_error = ""
        for idx, model in enumerate(Config.GROQ_LLM_MODELS):
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 250,
                    "response_format": {"type": "json_object"}
                }

                response = requests.post(url, headers=headers, json=payload, timeout=8)
                if response.status_code == 200:
                    res_data = response.json()
                    raw_response = res_data["choices"][0]["message"]["content"].strip()
                    data = json.loads(raw_response)
                    
                    reply = data.get("reply", "Sahayak at your service.")
                    action = data.get("action", {"type": "none", "params": {}})
                    res = {"reply": reply, "action": action}

                    self._record_history(user_text, res)
                    return res
                elif response.status_code == 429:
                    last_error = f"Rate limit on {model} (429)"
                    print(f"[AIEngine Warning] {last_error}, retrying next model...")
                    time.sleep(0.3)
                    continue
                elif response.status_code in [404, 400]:
                    last_error = f"Model {model} error ({response.status_code})"
                    continue
                else:
                    last_error = f"Groq API status {response.status_code}"
                    print(f"[AIEngine Error] {last_error}")
                    continue
            except Exception as e:
                last_error = str(e)
                print(f"[AIEngine Exception] {last_error}")
                continue

        # If all API calls fail/rate limit out, use intelligent local fallback
        print(f"[AIEngine] API rate limited ({last_error}). Using smart local fallback.")
        local_res = self._fallback_local_intent(user_text)
        if local_res:
            self._record_history(user_text, local_res)
            return local_res

        fallback_res = {
            "reply": "Main aapki baat samajh gaya hoon. Task process ho raha hai.",
            "action": {"type": "search_web", "params": {"query": user_text}}
        }
        self._record_history(user_text, fallback_res)
        return fallback_res


    def _fallback_local_intent(self, user_text: str) -> dict | None:
        """Smart local fallback parser when Groq API is offline or rate-limited."""
        lower = user_text.lower().strip()
        
        # Check domain patterns
        if "youtube" in lower:
            return {"reply": "Opening YouTube.", "action": {"type": "open_url", "params": {"url": "https://www.youtube.com"}}}
        elif "google" in lower:
            return {"reply": "Opening Google.", "action": {"type": "open_url", "params": {"url": "https://www.google.com"}}}
        elif "github" in lower:
            return {"reply": "Opening GitHub.", "action": {"type": "open_url", "params": {"url": "https://github.com"}}}
        elif "instagram" in lower:
            return {"reply": "Opening Instagram.", "action": {"type": "open_url", "params": {"url": "https://www.instagram.com"}}}
        
        # Search commands
        if lower.startswith("search ") or lower.startswith("dhoondo ") or lower.startswith("find "):
            query = re.sub(r'^(search|dhoondo|find)\s+', '', lower, flags=re.IGNORECASE)
            return {"reply": f"Searching for {query}.", "action": {"type": "search_web", "params": {"query": query}}}

        return None


    def _check_heuristics(self, user_text: str) -> dict | None:
        """Instant heuristic matching for web interactions, portals, and apps."""
        lower_text = user_text.lower().strip()

        # 1. Web interaction voice shortcuts & Language Popups
        if any(w in lower_text for w in ["english", "angrezi", "select english", "choose english"]):
            return {"reply": "English language select kar raha hoon.", "action": {"type": "select_language", "params": {"lang": "english"}}}
        elif any(w in lower_text for w in ["hindi", "select hindi", "choose hindi", "hindi language"]):
            return {"reply": "Hindi bhasha select kar raha hoon.", "action": {"type": "select_language", "params": {"lang": "hindi"}}}
        elif any(w in lower_text for w in ["scroll down", "niche scroll", "down scroll", "page down", "scroll niche"]):
            return {"reply": "Scrolling down.", "action": {"type": "scroll", "params": {"direction": "down"}}}
        elif any(w in lower_text for w in ["scroll up", "upar scroll", "up scroll", "page up", "scroll upar"]):
            return {"reply": "Scrolling up.", "action": {"type": "scroll", "params": {"direction": "up"}}}
        elif any(w in lower_text for w in ["press enter", "enter press", "enter key", "enter daba"]):
            return {"reply": "Pressing Enter.", "action": {"type": "press_key", "params": {"key": "enter"}}}
        elif any(w in lower_text for w in ["press tab", "tab press", "tab key"]):
            return {"reply": "Pressing Tab.", "action": {"type": "press_key", "params": {"key": "tab"}}}
        elif any(w in lower_text for w in ["go back", "page back", "piche jao"]):
            return {"reply": "Going back.", "action": {"type": "navigate_browser", "params": {"nav": "back"}}}
        elif any(w in lower_text for w in ["refresh page", "reload page", "page refresh"]):
            return {"reply": "Refreshing page.", "action": {"type": "navigate_browser", "params": {"nav": "refresh"}}}
        elif any(w in lower_text for w in ["close tab", "tab close"]):
            return {"reply": "Closing tab.", "action": {"type": "navigate_browser", "params": {"nav": "close_tab"}}}
        elif lower_text in ["click", "click here", "click button"]:
            return {"reply": "Clicking button.", "action": {"type": "click_screen", "params": {}}}
        elif lower_text.startswith("type ") or lower_text.startswith("enter text "):
            text_val = re.sub(r'^(type|enter text)\s+', '', user_text, flags=re.IGNORECASE)
            return {"reply": f"Typing {text_val}.", "action": {"type": "type_input", "params": {"text": text_val}}}

        # 2. Train Search & IRCTC Form Filling
        if any(w in lower_text for w in ["train search", "train khoj", "train dhoond", "train ticket", "chennai se", "chennai to"]):
            from_st = "Chennai" if "chennai" in lower_text else "Delhi"
            to_st = "Delhi" if "delhi" in lower_text or "chennai" in lower_text else "Mumbai"
            return {
                "reply": f"IRCTC par {from_st} se {to_st} ke liye train search start kar raha hoon.",
                "action": {"type": "search_trains", "params": {"from_station": from_st, "to_station": to_st}}
            }

        # 3. Contest Participation & Registration
        if any(w in lower_text for w in ["participate", "register", "contest", "reel"]):
            return {
                "reply": "Contest registration ke liye Login / Participate page open kar raha hoon.",
                "action": {"type": "click_screen", "params": {}}
            }

        # 4. Government Portals
        if "irctc" in lower_text or "railway" in lower_text:
            return {
                "reply": "Opening IRCTC portal.",
                "action": {"type": "open_portal", "params": {"portal": "irctc"}}
            }
        elif "mygov" in lower_text or "my gov" in lower_text:
            return {
                "reply": "Opening MyGov portal.",
                "action": {"type": "open_portal", "params": {"portal": "mygov"}}
            }


        elif "aadhaar" in lower_text or "adhar" in lower_text or "uidai" in lower_text:
            return {
                "reply": "Opening Aadhaar portal.",
                "action": {"type": "open_portal", "params": {"portal": "aadhaar"}}
            }
        elif "voter" in lower_text:
            return {
                "reply": "Opening Voter ID portal.",
                "action": {"type": "open_portal", "params": {"portal": "voter"}}
            }
        elif "digilocker" in lower_text:
            return {
                "reply": "Opening DigiLocker.",
                "action": {"type": "open_portal", "params": {"portal": "digilocker"}}
            }
        elif "calculator" in lower_text:
            return {
                "reply": "Opening Calculator.",
                "action": {"type": "open_app", "params": {"app": "calculator"}}
            }
        elif "notepad" in lower_text:
            return {
                "reply": "Opening Notepad.",
                "action": {"type": "open_app", "params": {"app": "notepad"}}
            }
        return None

