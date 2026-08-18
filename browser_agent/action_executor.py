import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import Page
from browser_agent.models import AgentAction, ActionType, DOMElement
from browser_agent.browser_manager import BrowserManager
from browser_agent.errors import BrowserAgentError

class ActionExecutor:
    """Executes validated actions on Playwright Browser and Page instances."""

    @classmethod
    async def execute_action(cls, action: AgentAction, target_element: Optional[DOMElement], browser_manager: BrowserManager) -> Dict[str, Any]:
        """Executes validated action using Playwright APIs."""
        page: Page = await browser_manager.get_current_page()
        
        try:
            if action.action == ActionType.NAVIGATE:
                url = action.url or ""
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                print(f"[ActionExecutor] Navigating to {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                return {"success": True, "msg": f"Navigated to {url}"}

            elif action.action == ActionType.CLICK:
                selector = target_element.selector if target_element else action.target_selector
                if selector:
                    print(f"[ActionExecutor] Clicking element '{selector}'...")
                    try:
                        await page.click(selector, timeout=5000)
                    except Exception:
                        # Fallback click via bounding box if selector click fails
                        if target_element and target_element.bounding_box:
                            bbox = target_element.bounding_box
                            await page.mouse.click(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
                    return {"success": True, "msg": f"Clicked element {selector}"}
                raise BrowserAgentError("Click target selector missing.")

            elif action.action == ActionType.TYPE:
                selector = target_element.selector if target_element else action.target_selector
                text = action.text or ""
                if selector:
                    print(f"[ActionExecutor] Typing into '{selector}': '{text}'...")
                    await page.fill(selector, text, timeout=5000)
                    if action.key == "Enter" or action.key == "enter":
                        await page.keyboard.press("Enter")
                    return {"success": True, "msg": f"Typed '{text}' into {selector}"}
                raise BrowserAgentError("Type target selector missing.")

            elif action.action == ActionType.SELECT:
                selector = target_element.selector if target_element else action.target_selector
                val = action.text or ""
                if selector:
                    await page.select_option(selector, label=val, timeout=5000)
                    return {"success": True, "msg": f"Selected option '{val}' in {selector}"}

            elif action.action == ActionType.SCROLL:
                direction = action.direction.lower()
                amount = 600 if direction == "down" else -600
                await page.mouse.wheel(0, amount)
                return {"success": True, "msg": f"Scrolled {direction}"}

            elif action.action == ActionType.PRESS_KEY:
                key = action.key or "Enter"
                await page.keyboard.press(key)
                return {"success": True, "msg": f"Pressed key '{key}'"}

            elif action.action == ActionType.WAIT:
                await asyncio.sleep(2.0)
                return {"success": True, "msg": "Waited 2 seconds"}

            elif action.action == ActionType.GO_BACK:
                await page.go_back(wait_until="domcontentloaded", timeout=10000)
                return {"success": True, "msg": "Navigated back"}

            elif action.action == ActionType.SWITCH_TAB:
                idx = action.tab_index or 0
                await browser_manager.switch_page(idx)
                return {"success": True, "msg": f"Switched to tab {idx}"}

            elif action.action == ActionType.CLOSE_TAB:
                await browser_manager.close_page(page)
                return {"success": True, "msg": "Closed tab"}

            elif action.action == ActionType.ASK_USER:
                return {"success": True, "msg": "Waiting for user input"}

            elif action.action == ActionType.DONE:
                return {"success": True, "msg": "Task completed successfully"}

            elif action.action == ActionType.FAIL:
                return {"success": False, "msg": action.reason or "Task failed"}

            return {"success": False, "msg": f"Unsupported action type: {action.action}"}

        except Exception as e:
            return {"success": False, "msg": f"Action execution error: {e}"}
