import asyncio
import time
from typing import Optional, Callable
from browser_agent.models import AgentState, ActionType, TaskModel, AgentAction, SafetyLevel, AgentEvent
from browser_agent.browser_manager import BrowserManager
from browser_agent.page_observer import PageObserver
from browser_agent.llm_reasoner import LLMReasoner
from browser_agent.action_validator import ActionValidator
from browser_agent.action_executor import ActionExecutor
from browser_agent.safety_manager import SafetyManager
from browser_agent.state_manager import StateManager
from browser_agent.errors import BrowserAgentError, ActionValidationError, SafetyConfirmationRequired, ActionLimitExceededError, TaskTimeoutError

class AgentLoop:
    """
    Main Autonomous Iterative Loop:
    OBSERVE -> UNDERSTAND -> PLAN -> DECIDE -> ACT -> VERIFY -> OBSERVE AGAIN
    """
    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        event_listener: Optional[Callable[[AgentEvent], None]] = None,
        max_actions: int = 50,
        max_retries: int = 3,
        timeout_seconds: float = 600.0
    ):
        self.browser_manager = browser_manager or BrowserManager(headless=False)
        self.state_manager = StateManager(event_listener=event_listener)
        self.max_actions = max_actions
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def execute_task(self, user_goal: str) -> TaskModel:
        """Executes full autonomous web agent loop for given user goal."""
        task = self.state_manager.create_task(user_goal)
        start_time = time.time()

        try:
            # Phase 1: Launch Browser
            self.state_manager.update_state(task.task_id, AgentState.OPENING_BROWSER, "Launching Playwright browser...")
            page = await self.browser_manager.launch()

            retry_count = 0

            # Core Iterative Loop
            while task.status not in [AgentState.COMPLETED, AgentState.FAILED, AgentState.WAITING_FOR_USER]:

                # Loop Protection Checks
                if len(task.steps_completed) >= self.max_actions:
                    raise ActionLimitExceededError(f"Task exceeded maximum action step limit of {self.max_actions}.")

                if (time.time() - start_time) > self.timeout_seconds:
                    raise TaskTimeoutError(f"Task timed out after {self.timeout_seconds} seconds.")

                # STEP 1: OBSERVE
                self.state_manager.update_state(task.task_id, AgentState.OBSERVING, "Observing webpage DOM & accessibility state...")
                page = await self.browser_manager.get_current_page()
                observation = await PageObserver.observe(page, is_initial_load=(len(task.steps_completed) == 0))
                
                task.current_url = observation.url
                task.current_page_title = observation.title

                # STEP 2: UNDERSTAND & PLAN
                self.state_manager.update_state(task.task_id, AgentState.PLANNING, "AI reasoning over page observation...")
                action: AgentAction = await LLMReasoner.plan_next_action(user_goal, observation, task.steps_completed)

                # STEP 3: DECIDE & SAFETY EVALUATION
                self.state_manager.update_state(task.task_id, AgentState.UNDERSTANDING, f"Evaluating action '{action.action.value}'...")
                safety_level, safety_msg = SafetyManager.evaluate_action_safety(action, observation.url)

                if safety_level == SafetyLevel.BLOCKED:
                    self.state_manager.update_state(task.task_id, AgentState.FAILED, safety_msg)
                    task.error_message = safety_msg
                    break

                if safety_level == SafetyLevel.CONFIRM_REQUIRED or action.action == ActionType.ASK_USER:
                    question = action.question or f"Sahayak needs your confirmation to execute: {action.reason}"
                    options = action.options or [{"label": "Proceed", "value": "proceed"}, {"label": "Cancel", "value": "cancel"}]
                    self.state_manager.set_waiting_for_user(task.task_id, question, options, action)
                    break

                # Termination actions
                if action.action == ActionType.DONE:
                    self.state_manager.update_state(task.task_id, AgentState.COMPLETED, action.reason or "Goal completed.")
                    break

                if action.action == ActionType.FAIL:
                    self.state_manager.update_state(task.task_id, AgentState.FAILED, action.reason or "Goal failed.")
                    task.error_message = action.reason
                    break

                # STEP 4: VALIDATE ACTION
                try:
                    target_element = ActionValidator.validate_action(action, observation)
                except ActionValidationError as val_err:
                    print(f"[AgentLoop Warning] Action validation error: {val_err}")
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        raise val_err
                    await asyncio.sleep(1.0)
                    continue

                # STEP 5: ACT
                self.state_manager.update_state(task.task_id, AgentState.EXECUTING, f"Executing {action.action.value} on {observation.url[:30]}...")
                result = await ActionExecutor.execute_action(action, target_element, self.browser_manager)

                # STEP 6: VERIFY
                self.state_manager.update_state(task.task_id, AgentState.VERIFYING, "Verifying page state post-action...")
                await asyncio.sleep(1.0)  # Brief wait for DOM stabilization
                
                post_page = await self.browser_manager.get_current_page()
                post_url = post_page.url
                
                verification_success = result.get("success", False)
                self.state_manager.record_step(task.task_id, action, post_url, verification_success)
                
                if verification_success:
                    retry_count = 0
                else:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        print(f"[AgentLoop Warning] Action failed {self.max_retries} times. Re-planning.")

        except Exception as ex:
            print(f"[AgentLoop Exception] Task execution failed: {ex}")
            self.state_manager.update_state(task.task_id, AgentState.FAILED, str(ex))
            task.error_message = str(ex)

        return task

    async def resume_task(self, task_id: str, user_response: str) -> TaskModel:
        """Resumes task after user provides input or confirmation."""
        task = self.state_manager.get_task(task_id)
        if not task or not task.pending_action:
            raise BrowserAgentError(f"Task '{task_id}' cannot be resumed.")

        self.state_manager.resume_user_input(task_id, user_response)
        pending = task.pending_action

        if user_response.lower() in ["cancel", "no", "reject"]:
            self.state_manager.cancel_task(task_id, "User cancelled confirmation.")
            return task

        # If user picked a choice from options (e.g. "English" or "Hindi" for language selection)
        if pending.action == ActionType.ASK_USER:
            # Map choice to language or click action
            user_choice = user_response.strip()
            print(f"[AgentLoop] Resuming task with user choice: '{user_choice}'")
            
            page = await self.browser_manager.get_current_page()
            observation = await PageObserver.observe(page)
            
            # Find matching element on page for user choice
            matched_id = None
            for elem in observation.elements:
                if elem.text.lower() == user_choice.lower():
                    matched_id = elem.id
                    break
            
            if matched_id:
                exec_action = AgentAction(action=ActionType.CLICK, target_id=matched_id, reason=f"Executing user selection '{user_choice}'.")
            else:
                exec_action = AgentAction(action=ActionType.CLICK, target_selector=f"text='{user_choice}'", reason=f"Executing user selection '{user_choice}'.")

            target_element = ActionValidator.validate_action(exec_action, observation)
            result = await ActionExecutor.execute_action(exec_action, target_element, self.browser_manager)
            self.state_manager.record_step(task_id, exec_action, page.url, result.get("success", False))

        # Continue autonomous loop
        task.pending_action = None
        task.waiting_for_user = False
        return await self.execute_task(task.user_goal)

    async def close(self):
        await self.browser_manager.close()
