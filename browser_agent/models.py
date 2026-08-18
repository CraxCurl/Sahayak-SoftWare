import time
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

class AgentState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    OPENING_BROWSER = "OPENING_BROWSER"
    OBSERVING = "OBSERVING"
    UNDERSTANDING = "UNDERSTANDING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"

class ActionType(str, Enum):
    NAVIGATE = "NAVIGATE"
    CLICK = "CLICK"
    TYPE = "TYPE"
    SELECT = "SELECT"
    CHECK = "CHECK"
    UNCHECK = "UNCHECK"
    SCROLL = "SCROLL"
    PRESS_KEY = "PRESS_KEY"
    WAIT = "WAIT"
    GO_BACK = "GO_BACK"
    GO_FORWARD = "GO_FORWARD"
    SWITCH_TAB = "SWITCH_TAB"
    CLOSE_TAB = "CLOSE_TAB"
    ASK_USER = "ASK_USER"
    DONE = "DONE"
    FAIL = "FAIL"

class SafetyLevel(str, Enum):
    SAFE = "SAFE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    BLOCKED = "BLOCKED"

@dataclass
class DOMElement:
    id: str
    tag: str
    role: str = "element"
    text: str = ""
    aria_label: str = ""
    placeholder: str = ""
    visible: bool = True
    enabled: bool = True
    clickable: bool = True
    bounding_box: Dict[str, float] = field(default_factory=dict)
    selector: str = ""
    is_modal_element: bool = False
    attributes: Dict[str, str] = field(default_factory=dict)

@dataclass
class PageObservation:
    url: str
    title: str
    hostname: str
    viewport: Dict[str, int]
    tabs: List[Dict[str, str]] = field(default_factory=list)
    active_tab_index: int = 0
    elements: List[DOMElement] = field(default_factory=list)
    accessibility_tree: str = ""
    screenshot_b64: Optional[str] = None
    has_modal: bool = False
    modal_title: str = ""
    modal_text: str = ""
    is_captcha: bool = False
    is_otp: bool = False

@dataclass
class AgentAction:
    action: ActionType
    target_id: Optional[str] = None
    target_selector: Optional[str] = None
    text: Optional[str] = None
    key: Optional[str] = None
    url: Optional[str] = None
    tab_index: Optional[int] = None
    reason: str = ""
    question: Optional[str] = None
    options: List[Dict[str, str]] = field(default_factory=list)
    direction: str = "down"

@dataclass
class TaskStepRecord:
    step_number: int
    state: AgentState
    action_taken: Optional[Dict[str, Any]]
    url: str
    verification_success: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class TaskModel:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_goal: str = ""
    status: AgentState = AgentState.IDLE
    current_url: str = ""
    current_page_title: str = ""
    current_step: str = "Initializing task"
    steps_completed: List[TaskStepRecord] = field(default_factory=list)
    pending_action: Optional[AgentAction] = None
    waiting_for_user: bool = False
    user_question: Optional[str] = None
    user_options: List[Dict[str, str]] = field(default_factory=list)
    user_response: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class AgentEvent:
    event_type: str
    task_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
