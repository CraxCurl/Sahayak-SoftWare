import webbrowser
import subprocess
import urllib.parse
import os
import sys
import time
from actions.portal_registry import resolve_portal, PORTALS
from core.web_automation import WebAutomation

class ActionRunner:
    last_opened_url = None
    last_opened_time = 0

    @classmethod
    def execute(cls, action_type: str, params: dict) -> dict:
        """
        Executes the specified action and returns status & message.
        Prevents repeating browser tab openings for the same URL in short succession.
        Supports interactive guided browser flows (Aadhaar update, login, OTP).
        """
        try:
            current_time = time.time()

            if action_type == "browser_agent":
                instruction = params.get("instruction", "")
                thread = threading.Thread(target=cls._run_browser_agent_thread, args=(instruction,), daemon=True)
                thread.start()
                return {"success": True, "msg": f"Started Sahayak Browser Agent for '{instruction}'."}

            elif action_type == "guided_flow":
                flow_name = params.get("flow", "")
                user_text = params.get("user_text", "")
                return WebAutomation.run_guided_flow(flow_name, user_text)


            elif action_type == "scroll":
                direction = params.get("direction", "down")
                WebAutomation.scroll_webpage(direction)
                return {"success": True, "msg": f"Scrolled {direction}."}

            elif action_type == "press_key":
                key_name = params.get("key", "enter")
                WebAutomation.press_key(key_name)
                return {"success": True, "msg": f"Pressed {key_name} key."}

            elif action_type == "type_input":
                text = params.get("text", "")
                WebAutomation.fill_input_text(text)
                return {"success": True, "msg": f"Typed '{text}' into web form."}

            elif action_type == "navigate_browser":
                nav = params.get("nav", "back")
                WebAutomation.navigate_browser(nav)
                return {"success": True, "msg": f"Browser navigation: {nav}."}

            elif action_type == "click_screen":
                WebAutomation.click_screen()
                return {"success": True, "msg": "Clicked screen element."}

            elif action_type == "select_language":
                lang = params.get("lang", "english")
                WebAutomation.select_language_popup(lang)
                return {"success": True, "msg": f"Selected language {lang} on popup."}

            elif action_type == "search_trains":
                from_st = params.get("from_station", "Chennai")
                to_st = params.get("to_station", "Delhi")
                date_str = params.get("date", "")
                return WebAutomation.search_irctc_trains(from_st, to_st, date_str)


            elif action_type == "open_url":
                url = params.get("url", "")
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url

                # Check if URL is IRCTC website -> run guided flow
                if "irctc" in url.lower():
                    return WebAutomation.run_guided_flow("irctc_language", url)

                # Deduplicate repeated URL opening within 20 seconds
                if cls.last_opened_url == url and (current_time - cls.last_opened_time) < 20:
                    return {"success": True, "msg": f"{url} is already open."}

                cls.last_opened_url = url
                cls.last_opened_time = current_time
                webbrowser.open(url)
                return {"success": True, "msg": f"Opened {url} in browser."}

            elif action_type == "open_portal":
                portal_name = params.get("portal", "")
                resolved = resolve_portal(portal_name)
                
                if resolved:
                    target_url = resolved["url"]
                    if cls.last_opened_url == target_url and (current_time - cls.last_opened_time) < 20:
                        return {"success": True, "msg": f"{resolved['name']} is already open."}

                    cls.last_opened_url = target_url
                    cls.last_opened_time = current_time

                    # Check if portal requires guided interactive interaction (Aadhaar update, IRCTC language selection)
                    if "aadhaar" in portal_name.lower() or "adhar" in portal_name.lower():
                        return WebAutomation.run_guided_flow("aadhaar_update", portal_name)
                    elif "irctc" in portal_name.lower() or "train" in portal_name.lower():
                        return WebAutomation.run_guided_flow("irctc_language", portal_name)

                    webbrowser.open(target_url)
                    return {"success": True, "msg": f"Opened {resolved['name']} ({target_url})"}

                else:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(portal_name + ' portal india')}"
                    if cls.last_opened_url == search_url and (current_time - cls.last_opened_time) < 20:
                        return {"success": True, "msg": f"Search for {portal_name} already opened."}

                    cls.last_opened_url = search_url
                    cls.last_opened_time = current_time
                    webbrowser.open(search_url)
                    return {"success": True, "msg": f"Searching for {portal_name} portal on Google."}

            elif action_type == "search_web":
                query = params.get("query", "")
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                if cls.last_opened_url == search_url and (current_time - cls.last_opened_time) < 20:
                    return {"success": True, "msg": f"Search for '{query}' already opened."}

                cls.last_opened_url = search_url
                cls.last_opened_time = current_time
                webbrowser.open(search_url)
                return {"success": True, "msg": f"Searched web for: '{query}'"}

            elif action_type == "open_app":
                app_name = params.get("app", "").lower()
                if "notepad" in app_name:
                    subprocess.Popen(["notepad.exe"])
                    return {"success": True, "msg": "Opened Notepad."}
                elif "calc" in app_name or "calculator" in app_name:
                    subprocess.Popen(["calc.exe"])
                    return {"success": True, "msg": "Opened Calculator."}
                elif "chrome" in app_name or "browser" in app_name:
                    webbrowser.open("https://www.google.com")
                    return {"success": True, "msg": "Opened Web Browser."}
                elif "cmd" in app_name or "terminal" in app_name:
                    subprocess.Popen(["start", "cmd"], shell=True)
                    return {"success": True, "msg": "Opened Command Prompt."}
                else:
                    return {"success": False, "msg": f"Application '{app_name}' not configured."}

            elif action_type == "none" or not action_type:
                return {"success": True, "msg": "Answering query."}

            else:
                return {"success": False, "msg": f"Unknown action type: {action_type}"}

        except Exception as e:
            return {"success": False, "msg": f"Failed to execute action: {str(e)}"}

    @classmethod
    def _run_browser_agent_thread(cls, instruction: str):
        """Runs the Playwright AgentLoop asynchronously in a dedicated thread."""
        try:
            import asyncio
            from browser_agent.agent_loop import AgentLoop
            print(f"[ActionRunner] Spawning Playwright BrowserAgent thread for: '{instruction}'...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            agent_loop = AgentLoop(max_actions=30, timeout_seconds=300.0)
            task = loop.run_until_complete(agent_loop.execute_task(instruction))
            
            print(f"[ActionRunner] BrowserAgent task completed with status: {task.status}")
        except Exception as e:
            print(f"[ActionRunner Exception] BrowserAgent error: {e}")


