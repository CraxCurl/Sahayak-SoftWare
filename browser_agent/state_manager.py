import time
from typing import List, Callable, Optional, Dict, Any
from browser_agent.models import TaskModel, AgentState, AgentAction, AgentEvent, TaskStepRecord

class StateManager:
    """Tracks task state transitions, records steps, and broadcasts real-time agent events."""

    def __init__(self, event_listener: Optional[Callable[[AgentEvent], None]] = None):
        self.event_listener = event_listener
        self.active_tasks: Dict[str, TaskModel] = {}

    def create_task(self, user_goal: str) -> TaskModel:
        task = TaskModel(user_goal=user_goal, status=AgentState.IDLE)
        self.active_tasks[task.task_id] = task
        self.emit_event("TASK_STARTED", task.task_id, {"user_goal": user_goal})
        return task

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        return self.active_tasks.get(task_id)

    def update_state(self, task_id: str, new_state: AgentState, step_msg: str = ""):
        task = self.get_task(task_id)
        if task:
            task.status = new_state
            if step_msg:
                task.current_step = step_msg
            task.updated_at = time.time()
            self.emit_event(f"STATE_{new_state.value}", task_id, {"state": new_state.value, "step": step_msg})

    def record_step(self, task_id: str, action: AgentAction, url: str, success: bool):
        task = self.get_task(task_id)
        if task:
            step_record = TaskStepRecord(
                step_number=len(task.steps_completed) + 1,
                state=task.status,
                action_taken={"action": action.action.value, "reason": action.reason, "url": action.url},
                url=url,
                verification_success=success
            )
            task.steps_completed.append(step_record)
            task.updated_at = time.time()
            self.emit_event("STEP_COMPLETED", task_id, {"step_number": step_record.step_number, "success": success})

    def set_waiting_for_user(self, task_id: str, question: str, options: List[Dict[str, str]], action: AgentAction):
        task = self.get_task(task_id)
        if task:
            task.status = AgentState.WAITING_FOR_USER
            task.waiting_for_user = True
            task.user_question = question
            task.user_options = options
            task.pending_action = action
            task.updated_at = time.time()
            self.emit_event("USER_INPUT_REQUIRED", task_id, {
                "question": question,
                "options": options
            })

    def resume_user_input(self, task_id: str, user_response: str):
        task = self.get_task(task_id)
        if task:
            task.user_response = user_response
            task.waiting_for_user = False
            task.status = AgentState.EXECUTING
            task.updated_at = time.time()
            self.emit_event("USER_INPUT_PROVIDED", task_id, {"response": user_response})

    def cancel_task(self, task_id: str, reason: str = "User cancelled task"):
        task = self.get_task(task_id)
        if task:
            task.status = AgentState.FAILED
            task.error_message = reason
            task.updated_at = time.time()
            self.emit_event("TASK_CANCELLED", task_id, {"reason": reason})

    def emit_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        event = AgentEvent(event_type=event_type, task_id=task_id, payload=payload)
        if self.event_listener:
            try:
                self.event_listener(event)
            except Exception as e:
                print(f"[StateManager Error] Event listener failed: {e}")
