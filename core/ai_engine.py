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
   - Example (English): "MyGov portal is open. You have options for Login, Mural Design Contest, and Citizen Quiz. Would you like to login or view contests?"
   - Example (Hindi): "मायगॉव पोर्टल खुला है। यहाँ लॉगिन, म्यूरल डिज़ाइन प्रतियोगिता और क्विज़ के विकल्प उपलब्ध हैं। क्या आप लॉगिन करना चाहते हैं?"
3. PROACTIVE FORM INPUT PROMPTS: When a user wants to fill out a form or perform a search (e.g. train ticket search, login form, registration):
   - Ask the user for the necessary input fields over voice!
   - Example (English): "To search trains: Please provide the Departure and Destination stations."
   - Example (Hindi): "ट्रेन खोजने के लिए: कृपया प्रस्थान और गंतव्य स्टेशन का नाम बताएं।"
4. NO UNNECESSARY CONFIRMATIONS ON URLS: When user specifies a URL/portal to open, execute immediately.
5. CONCISE SPOKEN RESPONSES: Keep your spoken 'reply' clear and brief (1-2 sentences max).
6. LANGUAGE SELECTION & RESPONSE RULES (STRICT):
   - If user speaks in English OR Hinglish (Hindi + English mixed together, or Hindi written in Latin/English alphabet like 'kholo', 'karo', 'dikhao', 'login kar do', 'train ticket check karo', etc.): You MUST ALWAYS RESPOND IN CLEAN, NATURAL ENGLISH. Never respond in Hinglish.
   - ONLY if the user speaks in PURE Hindi (written in Devanagari script or pure Hindi vocabulary): You MUST respond in pure Hindi (using Devanagari script).
   - If an explicit language mode is requested (e.g., 'speak in English', 'speak in Hindi', 'Hindi mein bolo'): Respond ONLY in that locked language until requested otherwise.
7. Return ONLY a valid JSON object.

JSON FORMAT SCHEMA:
{{
  "reply": "Clear response with action suggestion or form prompt if needed",
  "action": {{
    "type": "open_url" | "open_portal" | "guided_flow" | "fill_demo_form" | "scroll" | "press_key" | "type_input" | "navigate_browser" | "click_screen" | "search_web" | "open_app" | "browser_agent" | "none",
    "params": {{ ... }}
  }}
}}

AVAILABLE PORTALS MATCHING KEYWORDS:
{json.dumps({k: v['keywords'] for k, v in PORTALS.items()}, indent=2)}
"""


class AIEngine:
    def __init__(self):
        self.history = []
        self.preferred_language = "auto"  # "auto", "en", "hi", etc.

    def reset_history(self):
        """Resets conversation history while preserving explicit language preferences."""
        self.history = []

    def set_language(self, lang: str):
        """Explicitly sets or locks the response language ('en', 'hi', 'auto', etc.)."""
        self.preferred_language = lang.lower().strip()

    def _is_pure_hindi(self, text: str) -> bool:
        """
        Determines if text is in pure Hindi (Devanagari script without substantial Latin/English letters).
        Returns False for Hinglish (Latin script) and English.
        """
        if not text:
            return False

        has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
        has_latin = bool(re.search(r'[a-zA-Z]', text))

        if has_devanagari and not has_latin:
            return True
        elif has_devanagari and has_latin:
            devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
            latin_count = len(re.findall(r'[a-zA-Z]', text))
            return devanagari_count > (latin_count * 3)
        return False

    def _get_effective_language(self, user_text: str) -> str:
        """
        Determines the active response language:
        1. If user set an explicit language (not 'auto'), respect it.
        2. If in 'auto' mode:
           - Pure Hindi -> 'hi'
           - Hinglish or English -> 'en'
        """
        if self.preferred_language and self.preferred_language != "auto":
            return self.preferred_language

        return "hi" if self._is_pure_hindi(user_text) else "en"

    def _localize(self, en_text: str, hi_text: str, user_text: str = "") -> str:
        """Helper to return localized string based on active response language."""
        lang = self._get_effective_language(user_text)
        return hi_text if lang == "hi" else en_text

    def _check_language_switch(self, user_text: str) -> tuple[dict | None, str]:
        """
        Checks if user commanded an explicit language change (e.g. 'speak in english', 'hindi me bolo').
        Supports standalone commands and compound commands ('speak in english and open youtube').
        Returns (result_dict, remaining_user_text).
        """
        lower_text = user_text.lower().strip()

        # 0. If user says 'chuno', 'choose', 'chus', 'select', 'popup', 'button', 'irctc' -> skip voice language switch
        if any(w in lower_text for w in ["chuno", "chun", "choose", "chus", "select", "popup", "button", "irctc", "selete"]):
            return None, user_text

        # 1. English Switch Patterns
        en_patterns = [
            r'\b(?:please\s+)?(?:speak|talk|reply|respond|answer|chat)\s+(?:in|only\s+in)\s+english\b',
            r'\b(?:switch|change|set)\s+(?:to|language\s+to)\s+english\b',
            r'\b(?:talk\s+to\s+me\s+in|talk\s+in)\s+english\b',
            r'\b(?:only\s+speak\s+in|only\s+in)\s+english\b',
            r'\benglish\s+(?:mein?|me)\s+(?:bolo|baat\s+karo|jawab\s+do|baat\s+karein)\b',
            r'\b(?:shuddh|pure)?\s*english\s+(?:mein?|me)\s+(?:bolo|baat\s+karo)\b',
            r'\b(?:अंग्रेजी|इंग्लिश)\s*में\s*(?:बोलो|बात\s*करो|जवाब\s*दो)\b',
            r'^(?:speak\s+english|talk\s+english|only\s+speak\s+english|speak\s+only\s+english)$'
        ]

        # 2. Hindi Switch Patterns
        hi_patterns = [
            r'\b(?:please\s+)?(?:speak|talk|reply|respond|answer|chat)\s+(?:in|only\s+in)\s+hindi\b',
            r'\b(?:switch|change|set)\s+(?:to|language\s+to)\s+hindi\b',
            r'\b(?:talk\s+to\s+me\s+in|talk\s+in)\s+hindi\b',
            r'\b(?:only\s+speak\s+in|only\s+in)\s+hindi\b',
            r'\bhindi\s+(?:mein?|me)\s+(?:bolo|baat\s+karo|jawab\s+do|baat\s+karein)\b',
            r'\b(?:shuddh|pure|shudh)\s+hindi\s+(?:mein?|me)?\s*(?:bolo|baat\s+karo)?\b',
            r'\b(?:हिंदी|हिन्दी)\s*में\s*(?:बोलो|बात\s*करो|जवाब\s*दो)\b',
            r'\bशुद्ध\s*(?:हिंदी|हिन्दी)\s*(?:में\s*(?:बोलो|बात\s*करो))?\b',
            r'^(?:speak\s+hindi|talk\s+hindi|only\s+speak\s+hindi|speak\s+only\s+hindi)$'
        ]

        # 3. Auto / Reset Mode Patterns
        auto_patterns = [
            r'\b(?:reset\s+language|auto\s+language|default\s+language|automatic\s+language|auto\s+mode)\b',
            r'\blanguage\s+reset\b'
        ]

        # Test English patterns
        for pattern in en_patterns:
            if re.search(pattern, lower_text):
                self.preferred_language = "en"
                remaining = re.sub(pattern, '', user_text, count=1, flags=re.IGNORECASE).strip()
                remaining = re.sub(r'^(?:and|aur|then|also|please)\s+', '', remaining, flags=re.IGNORECASE).strip(" ,:.-")
                if remaining and len(remaining) > 2:
                    return None, remaining

                return {
                    "reply": "Sure, I will speak in English from now on.",
                    "action": {"type": "none", "params": {}}
                }, ""

        # Test Hindi patterns
        for pattern in hi_patterns:
            if re.search(pattern, lower_text):
                self.preferred_language = "hi"
                remaining = re.sub(pattern, '', user_text, count=1, flags=re.IGNORECASE).strip()
                remaining = re.sub(r'^(?:and|aur|then|also|please|और|कृपया)\s+', '', remaining, flags=re.IGNORECASE).strip(" ,:.-")
                if remaining and len(remaining) > 2:
                    return None, remaining

                return {
                    "reply": "ठीक है, अब से मैं केवल हिंदी में बात करूँगा।",
                    "action": {"type": "none", "params": {}}
                }, ""

        # Test Auto patterns
        for pattern in auto_patterns:
            if re.search(pattern, lower_text):
                self.preferred_language = "auto"
                return {
                    "reply": "Language mode reset to automatic.",
                    "action": {"type": "none", "params": {}}
                }, ""

        return None, user_text

    def _record_history(self, user_text: str, result: dict):
        """Records user prompt and assistant response into conversation history, maintaining 20-turn context."""
        try:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": json.dumps(result)})
            self.history = self.history[-20:]
        except Exception:
            pass

    def process_query(self, user_text: str) -> dict:
        """
        Processes user query with language control, long-term context retention, action suggestions, and form prompts.
        """
        # Step 0: Check if user commanded an explicit language switch
        switch_res, remaining_text = self._check_language_switch(user_text)
        if switch_res:
            self._record_history(user_text, switch_res)
            return switch_res

        active_query = remaining_text if remaining_text else user_text

        # Fast Heuristic 1: Check for explicit website domains
        domain_match = re.search(r'\b([a-zA-Z0-9-]+\.(?:com|in|ac\.in|org|net|edu|gov\.in|io|co))\b', active_query.lower())
        if domain_match:
            domain = domain_match.group(1)
            full_match = re.search(r'\b([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.(?:ac\.in|gov\.in|co\.in))\b', active_query.lower())
            if full_match:
                domain = full_match.group(1)

            target_url = f"https://{domain}"
            res = {
                "reply": self._localize(f"Opening {domain}.", f"{domain} खोल रहा हूँ।", active_query),
                "action": {"type": "open_url", "params": {"url": target_url}}
            }
            self._record_history(user_text, res)
            return res

        # Fast Heuristic 2: Check portal keywords & web shortcuts
        heuristic_res = self._check_heuristics(active_query)
        if heuristic_res:
            self._record_history(user_text, heuristic_res)
            return heuristic_res

        api_key = Config.get_api_key()
        if not api_key:
            res = {
                "reply": self._localize(
                    "Groq API Key missing. Add GROQ_API_KEY in Settings.",
                    "ग्रोक एपीआई कुंजी उपलब्ध नहीं है। कृपया सेटिंग्स में GROQ_API_KEY जोड़ें।",
                    active_query
                ),
                "action": {"type": "none", "params": {}}
            }
            self._record_history(user_text, res)
            return res

        effective_lang = self._get_effective_language(active_query)
        if self.preferred_language == "en":
            lang_directive = "MANDATORY LANGUAGE OVERRIDE: The user explicitly specified ENGLISH. You MUST respond ONLY in clean, natural English. Never use Hindi or Hinglish."
        elif self.preferred_language == "hi":
            lang_directive = "MANDATORY LANGUAGE OVERRIDE: The user explicitly specified HINDI. You MUST respond ONLY in pure Hindi (written in Devanagari script: \\u0900-\\u097F). Never use Hinglish or English."
        elif self.preferred_language and self.preferred_language != "auto":
            lang_directive = f"MANDATORY LANGUAGE OVERRIDE: The user explicitly specified {self.preferred_language.upper()}. You MUST respond ONLY in {self.preferred_language}."
        else:
            if effective_lang == "hi":
                lang_directive = "LANGUAGE DIRECTIVE: The user spoke in pure Hindi. You MUST respond in pure, polite Hindi (written in Devanagari script: \\u0900-\\u097F)."
            else:
                lang_directive = "LANGUAGE DIRECTIVE: The user spoke in English or Hinglish (Hindi-English mix). You MUST respond in clean, natural ENGLISH. Do NOT respond in Hinglish."

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        system_instruction = f"{SYSTEM_PROMPT}\n\n[ACTIVE LANGUAGE DIRECTIVE]\n{lang_directive}"
        messages = [{"role": "system", "content": system_instruction}]
        for hist in self.history[-12:]:
            messages.append(hist)
        messages.append({"role": "user", "content": active_query})

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

                    default_reply = self._localize("Sahayak at your service.", "सहायक आपकी सेवा में उपस्थित है।", active_query)
                    reply = data.get("reply", default_reply)
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
        local_res = self._fallback_local_intent(active_query)
        if local_res:
            self._record_history(user_text, local_res)
            return local_res

        fallback_res = {
            "reply": self._localize(
                "I understood your request. Processing task.",
                "मैं आपकी बात समझ गया हूँ। कार्य प्रक्रिया में है।",
                active_query
            ),
            "action": {"type": "search_web", "params": {"query": active_query}}
        }
        self._record_history(user_text, fallback_res)
        return fallback_res

    def _fallback_local_intent(self, user_text: str) -> dict | None:
        """Smart local fallback parser when Groq API is offline or rate-limited."""
        lower = user_text.lower().strip()

        # Check domain patterns
        if "youtube" in lower or "यूट्यूब" in lower:
            return {
                "reply": self._localize("Opening YouTube.", "यूट्यूब खोल रहा हूँ।", user_text),
                "action": {"type": "open_url", "params": {"url": "https://www.youtube.com"}}
            }
        elif "google" in lower or "गूगल" in lower:
            return {
                "reply": self._localize("Opening Google.", "गूगल खोल रहा हूँ।", user_text),
                "action": {"type": "open_url", "params": {"url": "https://www.google.com"}}
            }
        elif "github" in lower:
            return {
                "reply": self._localize("Opening GitHub.", "गिटहब खोल रहा हूँ।", user_text),
                "action": {"type": "open_url", "params": {"url": "https://github.com"}}
            }
        elif "instagram" in lower or "इंस्टाग्राम" in lower:
            return {
                "reply": self._localize("Opening Instagram.", "इंस्टाग्राम खोल रहा हूँ।", user_text),
                "action": {"type": "open_url", "params": {"url": "https://www.instagram.com"}}
            }

        # Search commands
        if lower.startswith("search ") or lower.startswith("dhoondo ") or lower.startswith("find ") or lower.startswith("खोजो "):
            query = re.sub(r'^(search|dhoondo|find|खोजो)\s+', '', lower, flags=re.IGNORECASE)
            return {
                "reply": self._localize(f"Searching for {query}.", f"{query} खोज रहा हूँ।", user_text),
                "action": {"type": "search_web", "params": {"query": query}}
            }

        return None

    def _extract_demo_form_details(self, text: str) -> dict | None:
        """Extracts user profile fields (first name, last name, age, state) for browser automation demo."""
        lower = text.lower()
        has_name_kw = "first name" in lower or "last name" in lower or "name is" in lower or "naam" in lower or "नाम" in lower
        has_age_kw = "age" in lower or "years old" in lower or "saal" in lower or "umar" in lower or "उम्र" in lower
        has_state_kw = "from" in lower or "state" in lower or "bihar" in lower or "rajya" in lower or "राज्य" in lower

        if (has_name_kw and (has_age_kw or has_state_kw)) or ("first name" in lower and "last name" in lower) or ("arpit" in lower and "raj" in lower):
            fn = "Arpit"
            ln = "Raj"
            age = "20"
            state = "Bihar"

            m_fn = re.search(r'(?:first\s+name\s*(?:is|=|:)?\s*|naam\s*(?:is|=|:)?\s*|नाम\s*(?:है|=|:)?\s*)([a-zA-Z\u0900-\u097F]+)', text, re.IGNORECASE)
            if m_fn:
                fn = m_fn.group(1).capitalize()

            m_ln = re.search(r'(?:last\s+name\s*(?:is|=|:)?\s*|surname\s*(?:is|=|:)?\s*)([a-zA-Z\u0900-\u097F]+)', text, re.IGNORECASE)
            if m_ln:
                ln = m_ln.group(1).capitalize()

            m_ag = re.search(r'(?:age\s*(?:is|=|:)?\s*|umar\s*(?:is|=|:)?\s*|उम्र\s*(?:है|=|:)?\s*)(\d+)', text, re.IGNORECASE)
            if m_ag:
                age = m_ag.group(1)
            else:
                m_ag_num = re.search(r'\b(\d{1,3})\s*(?:years|yr|saal|साल)?\s*(?:old|ka|ki)?\b', text, re.IGNORECASE)
                if m_ag_num and int(m_ag_num.group(1)) <= 120:
                    age = m_ag_num.group(1)

            m_st = re.search(r'(?:from\s+(?:state\s+)?|state\s*(?:is|=|:)?\s*|rajya\s*(?:is|=|:)?\s*|राज्य\s*(?:है|=|:)?\s*)([a-zA-Z\u0900-\u097F]+)', text, re.IGNORECASE)
            if m_st:
                state = m_st.group(1).capitalize()

            return {"first_name": fn, "last_name": ln, "age": age, "state": state}

        return None

    def _check_heuristics(self, user_text: str) -> dict | None:
        """Instant heuristic matching for web interactions, portals, and apps with full localization."""
        lower_text = user_text.lower().strip()

        # 0. Sahayak Demo Website & Automated Form Filling
        if any(w in lower_text for w in ["open demo", "demo website", "demo portal", "demo page", "demo site", "sahayak demo", "डेमो वेबसाइट", "डेमो खोल"]):
            en_reply = "Opening demo website. Please tell me your details like first name, last name, age, and state."
            hi_reply = "डेमो वेबसाइट खोल रहा हूँ। कृपया अपना विवरण जैसे नाम, उम्र और राज्य बताएं।"
            return {
                "reply": self._localize(en_reply, hi_reply, user_text),
                "action": {"type": "open_url", "params": {"url": "https://omthavari2006-dev.github.io/demo/"}}
            }

        demo_details = self._extract_demo_form_details(user_text)
        if demo_details:
            fn = demo_details["first_name"]
            ln = demo_details["last_name"]
            age = demo_details["age"]
            st = demo_details["state"]
            en_reply = f"Filling demo form with First Name {fn}, Last Name {ln}, Age {age}, State {st}, and logging in."
            hi_reply = f"डेमो फॉर्म भर रहा हूँ: नाम {fn} {ln}, उम्र {age}, राज्य {st} और लॉगिन कर रहा हूँ।"
            return {
                "reply": self._localize(en_reply, hi_reply, user_text),
                "action": {
                    "type": "fill_demo_form",
                    "params": {
                        "first_name": fn,
                        "last_name": ln,
                        "age": age,
                        "state": st
                    }
                }
            }

        # 1. Web interaction voice shortcuts & Language Popups on Webpages (IRCTC / Websites)
        is_voice_switch_explicit = any(w in lower_text for w in ["speak in", "talk in", "reply in", "me bolo", "mein bolo", "me baat", "mein baat", "me jawab", "mein jawab"])

        if not is_voice_switch_explicit:
            recent_context = json.dumps(self.history[-4:]).lower() if self.history else ""
            is_recent_lang_prompt = "irctc" in recent_context or "bhasha" in recent_context or "language" in recent_context or "chunein" in recent_context or "hindi ya english" in recent_context or "portal" in recent_context

            hindi_match = any(w in lower_text for w in [
                "hindi chus", "hindi choose", "hindi chuno", "hindi chun", "hindi select", "select hindi", "choose hindi",
                "hindi mein karo", "hindi me karo", "hindi bhasha", "hindi language", "hindi on popup", "popup hindi",
                "hindi button", "irctc hindi", "हिंदी चुनो", "हिंदी भाषा", "हिंदी सेलेक्ट", "हिंदी"
            ]) or (is_recent_lang_prompt and (lower_text in ["hindi", "हिंदी", "hindi me", "hindi mein", "hindi please"]))

            english_match = any(w in lower_text for w in [
                "english chus", "english choose", "english chuno", "english chun", "english select", "select english", "choose english",
                "english mein karo", "english me karo", "english bhasha", "english language", "english on popup", "popup english",
                "english button", "irctc english", "इंग्लिश चुनो", "इंग्लिश भाषा", "इंग्लिश सेलेक्ट", "अंग्रेजी चुनो"
            ]) or (is_recent_lang_prompt and (lower_text in ["english", "इंग्लिश", "अंग्रेजी", "english me", "english mein", "english please"]))

            if hindi_match:
                reply = self._localize("Selecting Hindi on IRCTC and closing popup.", "IRCTC पर हिंदी भाषा चुन रहा हूँ और अलर्ट बंद कर रहा हूँ।", user_text)
                return {"reply": reply, "action": {"type": "select_language", "params": {"lang": "hindi"}}}
            elif english_match:
                reply = self._localize("Selecting English on IRCTC and closing popup.", "IRCTC पर इंग्लिश भाषा चुन रहा हूँ और अलर्ट बंद कर रहा हूँ।", user_text)
                return {"reply": reply, "action": {"type": "select_language", "params": {"lang": "english"}}}

        # Scrolling
        elif any(w in lower_text for w in ["scroll down", "niche scroll", "down scroll", "page down", "scroll niche", "नीचे स्क्रॉल"]):
            return {
                "reply": self._localize("Scrolling down.", "नीचे स्क्रॉल कर रहा हूँ।", user_text),
                "action": {"type": "scroll", "params": {"direction": "down"}}
            }
        elif any(w in lower_text for w in ["scroll up", "upar scroll", "up scroll", "page up", "scroll upar", "ऊपर स्क्रॉल"]):
            return {
                "reply": self._localize("Scrolling up.", "ऊपर स्क्रॉल कर रहा हूँ।", user_text),
                "action": {"type": "scroll", "params": {"direction": "up"}}
            }

        # Keyboard Keys
        elif any(w in lower_text for w in ["press enter", "enter press", "enter key", "enter daba", "एंटर दबा"]):
            return {
                "reply": self._localize("Pressing Enter.", "एंटर दबा रहा हूँ।", user_text),
                "action": {"type": "press_key", "params": {"key": "enter"}}
            }
        elif any(w in lower_text for w in ["press tab", "tab press", "tab key", "टैब दबा"]):
            return {
                "reply": self._localize("Pressing Tab.", "टैब दबा रहा हूँ।", user_text),
                "action": {"type": "press_key", "params": {"key": "tab"}}
            }

        # Browser Navigation
        elif any(w in lower_text for w in ["go back", "page back", "piche jao", "पीछे जाओ"]):
            return {
                "reply": self._localize("Going back.", "पीछे जा रहा हूँ।", user_text),
                "action": {"type": "navigate_browser", "params": {"nav": "back"}}
            }
        elif any(w in lower_text for w in ["refresh page", "reload page", "page refresh", "पेज रीफ्रेश", "रीलोड"]):
            return {
                "reply": self._localize("Refreshing page.", "पेज रीफ़्रेश कर रहा हूँ।", user_text),
                "action": {"type": "navigate_browser", "params": {"nav": "refresh"}}
            }
        elif any(w in lower_text for w in ["close tab", "tab close", "टैब बंद"]):
            return {
                "reply": self._localize("Closing tab.", "टैब बंद कर रहा हूँ।", user_text),
                "action": {"type": "navigate_browser", "params": {"nav": "close_tab"}}
            }
        elif lower_text in ["click", "click here", "click button", "क्लिक करो", "क्लिक"]:
            return {
                "reply": self._localize("Clicking button.", "क्लिक कर रहा हूँ।", user_text),
                "action": {"type": "click_screen", "params": {}}
            }
        elif lower_text.startswith("type ") or lower_text.startswith("enter text ") or lower_text.startswith("टाइप करो "):
            text_val = re.sub(r'^(type|enter text|टाइप करो)\s+', '', user_text, flags=re.IGNORECASE)
            return {
                "reply": self._localize(f"Typing {text_val}.", f"टाइप कर रहा हूँ: {text_val}", user_text),
                "action": {"type": "type_input", "params": {"text": text_val}}
            }

        # 2. Train Search & IRCTC Form Filling
        if any(w in lower_text for w in ["train search", "train khoj", "train dhoond", "train ticket", "chennai se", "chennai to", "ट्रेन खोज", "ट्रेन टिकट"]):
            from_st = "Chennai" if "chennai" in lower_text or "चेन्नई" in lower_text else "Delhi"
            to_st = "Delhi" if "delhi" in lower_text or "दिल्ली" in lower_text or "chennai" in lower_text or "चेन्नई" in lower_text else "Mumbai"
            en_reply = f"Searching trains on IRCTC from {from_st} to {to_st}."
            hi_reply = f"आईआरसीटीसी पर {from_st} से {to_st} के लिए ट्रेन खोज रहा हूँ।"
            return {
                "reply": self._localize(en_reply, hi_reply, user_text),
                "action": {"type": "search_trains", "params": {"from_station": from_st, "to_station": to_st}}
            }

        # 3. Contest Participation & Registration
        if any(w in lower_text for w in ["participate", "register", "contest", "reel", "प्रतियोगिता", "भाग लें"]):
            return {
                "reply": self._localize("Opening Login / Participate page for contest.", "प्रतियोगिता के लिए लॉगिन / भाग लें पेज खोल रहा हूँ।", user_text),
                "action": {"type": "click_screen", "params": {}}
            }

        # 4. Government Portals
        if "irctc" in lower_text or "railway" in lower_text or "आईआरसीटीसी" in lower_text or "रेलवे" in lower_text:
            return {
                "reply": self._localize("Opening IRCTC portal.", "आईआरसीटीसी पोर्टल खोल रहा हूँ।", user_text),
                "action": {"type": "open_portal", "params": {"portal": "irctc"}}
            }
        elif "mygov" in lower_text or "my gov" in lower_text or "मायगॉव" in lower_text:
            return {
                "reply": self._localize("Opening MyGov portal.", "मायगॉव पोर्टल खोल रहा हूँ।", user_text),
                "action": {"type": "open_portal", "params": {"portal": "mygov"}}
            }
        elif "aadhaar" in lower_text or "adhar" in lower_text or "uidai" in lower_text or "आधार" in lower_text:
            return {
                "reply": self._localize("Opening Aadhaar portal.", "आधार पोर्टल खोल रहा हूँ।", user_text),
                "action": {"type": "open_portal", "params": {"portal": "aadhaar"}}
            }
        elif "voter" in lower_text or "वोटर" in lower_text:
            return {
                "reply": self._localize("Opening Voter ID portal.", "वोटर आईडी पोर्टल खोल रहा हूँ।", user_text),
                "action": {"type": "open_portal", "params": {"portal": "voter"}}
            }
        elif "digilocker" in lower_text or "डिजिलॉकर" in lower_text:
            return {
                "reply": self._localize("Opening DigiLocker.", "डिजिलॉकर खोल रहा हूँ।", user_text),
                "action": {"type": "open_portal", "params": {"portal": "digilocker"}}
            }
        elif "calculator" in lower_text or "कैलकुलेटर" in lower_text:
            return {
                "reply": self._localize("Opening Calculator.", "कैलकुलेटर खोल रहा हूँ।", user_text),
                "action": {"type": "open_app", "params": {"app": "calculator"}}
            }
        elif "notepad" in lower_text or "नोटपैड" in lower_text:
            return {
                "reply": self._localize("Opening Notepad.", "नोटपैड खोल रहा हूँ।", user_text),
                "action": {"type": "open_app", "params": {"app": "notepad"}}
            }
        return None

