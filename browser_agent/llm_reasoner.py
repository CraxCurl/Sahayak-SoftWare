import json
import re
import requests
from typing import List, Dict, Any, Optional
from config import Config
from browser_agent.models import AgentAction, ActionType, PageObservation, TaskStepRecord
from browser_agent.prompt_templates import PLANNER_SYSTEM_PROMPT
from browser_agent.popup_detector import PopupDetector

class LLMReasoner:
    """LLM Reasoning Engine producing validated structured actions for Sahayak Browser Agent."""

    @classmethod
    async def plan_next_action(cls, user_goal: str, observation: PageObservation, history: List[TaskStepRecord]) -> AgentAction:
        """Determines the next structured action to perform based on page observation and user goal."""

        # 1. Fast Heuristic Check for Popups (Language, Cookie, Login)
        popup_info = PopupDetector.detect_popup(observation.elements, observation.modal_text, observation.title)
        if popup_info["detected"]:
            if popup_info["requires_user"]:
                return AgentAction(
                    action=ActionType.ASK_USER,
                    question=popup_info["question"],
                    options=popup_info["options"],
                    reason=f"Detected {popup_info['title']} requiring user input."
                )
            elif popup_info.get("auto_target_id"):
                return AgentAction(
                    action=ActionType.CLICK,
                    target_id=popup_info["auto_target_id"],
                    reason=f"Automatically accepting {popup_info['title']}."
                )

        api_key = Config.get_api_key()
        if not api_key:
            # Fallback to direct navigation or user question if API key is missing
            if not observation.url or observation.url == "about:blank":
                return AgentAction(action=ActionType.NAVIGATE, url=cls._extract_url_from_goal(user_goal), reason="API key missing, using direct goal URL heuristic.")
            return AgentAction(action=ActionType.DONE, reason="Groq API Key missing.")

        # 2. Format compressed DOM observation for LLM
        compressed_elements = []
        for elem in observation.elements[:40]:
            compressed_elements.append({
                "id": elem.id,
                "role": elem.role,
                "text": elem.text,
                "aria_label": elem.aria_label,
                "placeholder": elem.placeholder,
                "selector": elem.selector,
                "is_modal": elem.is_modal_element
            })

        history_summary = []
        for step in history[-5:]:
            history_summary.append(f"Step {step.step_number}: Action {step.action_taken} -> Success: {step.verification_success}")

        user_content = f"""USER GOAL: {user_goal}

CURRENT PAGE STATE:
- URL: {observation.url}
- Title: {observation.title}
- Has Modal/Popup: {observation.has_modal}
- Modal Text: {observation.modal_text[:200] if observation.modal_text else 'None'}

ACCESSIBILITY SNAPSHOT:
{observation.accessibility_tree[:400]}

VISIBLE INTERACTIVE DOM ELEMENTS:
{json.dumps(compressed_elements, indent=2)}

RECENT ACTION HISTORY:
{chr(10).join(history_summary) if history_summary else 'No actions executed yet.'}

Select the next best action in strict JSON format.
"""

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Model Fallback Loop
        for model in Config.GROQ_LLM_MODELS:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"}
                }
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    raw_text = res.json()["choices"][0]["message"]["content"].strip()
                    return cls._parse_action_json(raw_text)
            except Exception as e:
                print(f"[LLMReasoner Warning] Model {model} failed: {e}")
                continue

        # Rule-based fallback if all models fail
        return cls._fallback_rule_reasoner(user_goal, observation)

    @classmethod
    def _parse_action_json(cls, json_str: str) -> AgentAction:
        """Parses LLM JSON response into validated AgentAction."""
        try:
            data = json.loads(json_str)
            action_type_str = data.get("action", "DONE").upper()
            action_enum = ActionType(action_type_str) if action_type_str in ActionType.__members__ else ActionType.DONE

            return AgentAction(
                action=action_enum,
                target_id=data.get("target_id"),
                target_selector=data.get("target_selector"),
                text=data.get("text"),
                key=data.get("key"),
                url=data.get("url"),
                tab_index=data.get("tab_index"),
                direction=data.get("direction", "down"),
                reason=data.get("reason", "LLM reasoning"),
                question=data.get("question"),
                options=data.get("options", [])
            )
        except Exception as e:
            print(f"[LLMReasoner Error] Failed to parse action JSON '{json_str}': {e}")
            return AgentAction(action=ActionType.DONE, reason="Parsing fallback")

    @classmethod
    def _extract_url_from_goal(cls, goal: str) -> str:
        """Extracts domain or URL from user goal string."""
        if "irctc" in goal.lower():
            return "https://www.irctc.co.in"
        elif "amazon" in goal.lower():
            return "https://www.amazon.in"
        elif "youtube" in goal.lower():
            return "https://www.youtube.com"
        elif "google" in goal.lower():
            return "https://www.google.com"
        
        match = re.search(r'https?://[^\s]+', goal)
        if match:
            return match.group(0)
        return "https://www.google.com"

    @classmethod
    def _fallback_rule_reasoner(cls, user_goal: str, observation: PageObservation) -> AgentAction:
        """Rule-based fallback when LLM API is unavailable."""
        if not observation.url or observation.url == "about:blank":
            return AgentAction(action=ActionType.NAVIGATE, url=cls._extract_url_from_goal(user_goal), reason="Initial navigation")
        
        return AgentAction(action=ActionType.DONE, reason="Goal completed via rule fallback.")
