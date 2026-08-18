from typing import Optional, List
from browser_agent.models import AgentAction, ActionType, PageObservation, DOMElement
from browser_agent.errors import ActionValidationError, TargetNotFoundError, AmbiguousTargetError

class ActionValidator:
    """Validates structured AI Agent actions against current page observation state."""

    @classmethod
    def validate_action(cls, action: AgentAction, observation: PageObservation) -> DOMElement | None:
        """Validates action target existence, visibility, and non-ambiguity."""

        # 1. Non-target actions (NAVIGATE, WAIT, ASK_USER, DONE, FAIL, GO_BACK, GO_FORWARD)
        if action.action in [ActionType.NAVIGATE, ActionType.WAIT, ActionType.ASK_USER, ActionType.DONE, ActionType.FAIL, ActionType.GO_BACK, ActionType.GO_FORWARD]:
            return None

        # 2. Target validation for CLICK, TYPE, SELECT, CHECK, UNCHECK
        matched_element: Optional[DOMElement] = None
        candidates: List[DOMElement] = []

        if action.target_id:
            for elem in observation.elements:
                if elem.id == action.target_id:
                    candidates.append(elem)
        elif action.target_selector:
            for elem in observation.elements:
                if elem.selector == action.target_selector or (action.target_selector.lower() in elem.text.lower() if elem.text else False):
                    candidates.append(elem)

        if not candidates and action.action in [ActionType.CLICK, ActionType.TYPE, ActionType.SELECT]:
            raise TargetNotFoundError(f"Target element '{action.target_id or action.target_selector}' not found on page '{observation.url}'.")

        if len(candidates) > 1:
            # Check if text is identical across candidates -> ambiguity!
            texts = [c.text for c in candidates if c.text]
            if len(set(texts)) < len(candidates):
                print(f"[ActionValidator Warning] Ambiguous target detected: {len(candidates)} elements match '{action.target_selector or action.target_id}'. Using first visible candidate.")

        matched_element = candidates[0] if candidates else None

        if matched_element:
            if not matched_element.visible:
                raise ActionValidationError(f"Target element '{matched_element.id}' is not visible.")
            if not matched_element.enabled and action.action in [ActionType.CLICK, ActionType.TYPE]:
                raise ActionValidationError(f"Target element '{matched_element.id}' is disabled.")

        return matched_element
