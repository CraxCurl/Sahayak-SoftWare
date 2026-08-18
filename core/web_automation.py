import time
import webbrowser
import threading
import urllib.parse
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None


from core.tts_engine import TTSEngine

class WebAutomation:
    """
    Automates interactive browser actions, form filling, screen button clicking,
    and step-by-step guided user flows (Aadhaar phone update, logins, OTP entry).
    """

    @classmethod
    def run_guided_flow(cls, flow_name: str, user_text: str, speech_callback=None) -> dict:
        """
        Executes a step-by-step interactive voice-guided web workflow in a background thread.
        """
        thread = threading.Thread(
            target=cls._guided_flow_worker,
            args=(flow_name, user_text, speech_callback),
            daemon=True
        )
        thread.start()
        return {"success": True, "msg": f"Started guided workflow for '{flow_name}'."}

    @classmethod
    def _guided_flow_worker(cls, flow_name: str, user_text: str, speech_callback):
        try:
            if "aadhaar" in flow_name or "adhar" in flow_name:
                url = "https://myaadhaar.uidai.gov.in"
                webbrowser.open(url)
                time.sleep(2.5)

                # Step 1: Sahayak speaks to user for input
                msg1 = "Aadhaar portal khol diya hai. Kripya apna 12-digit Aadhaar number ya Registered Phone number bataiye."
                print(f"[WebAutomation] Sahayak: {msg1}")
                TTSEngine.speak_async(msg1)

                # Step 2: Auto-focus and click input field if pyautogui is present
                if pyautogui:
                    time.sleep(1.0)
                    # Press Tab or Click center of screen to focus first input
                    pyautogui.press("tab")

            elif "login" in flow_name or "mygov" in flow_name:
                url = "https://www.mygov.in"
                webbrowser.open(url)
                time.sleep(2.0)

                msg = "MyGov portal khola ja raha hai. Sign in karne ke liye apna mobile number ya email bataiye."
                print(f"[WebAutomation] Sahayak: {msg}")
                TTSEngine.speak_async(msg)

            elif "irctc" in flow_name or "train" in flow_name:
                url = "https://www.irctc.co.in"
                webbrowser.open(url)
                time.sleep(2.5)

                msg = "IRCTC website khol diya hai. Kripya apni bhasha chunein: Hindi ya English?"
                print(f"[WebAutomation] Sahayak: {msg}")
                TTSEngine.speak_async(msg)

            elif "video" in flow_name or "youtube" in flow_name:
                query = user_text.replace("video", "").replace("khol do", "").replace("search", "").strip()
                search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                webbrowser.open(search_url)
                time.sleep(2.0)

                msg = f"YouTube par '{query}' search kar ke video khol diya hai."
                print(f"[WebAutomation] Sahayak: {msg}")
                TTSEngine.speak_async(msg)

            else:
                webbrowser.open("https://www.google.com")

        except Exception as e:
            print(f"[WebAutomation Exception] Guided flow error: {e}")

    @classmethod
    def search_irctc_trains(cls, from_station: str = "Chennai", to_station: str = "Delhi", date_str: str = "") -> dict:
        """Automates IRCTC train search form filling (From Station, To Station, Date, Search)."""
        thread = threading.Thread(
            target=cls._irctc_train_search_worker,
            args=(from_station, to_station, date_str),
            daemon=True
        )
        thread.start()
        return {"success": True, "msg": f"Searching IRCTC trains from {from_station} to {to_station}."}

    @classmethod
    def _irctc_train_search_worker(cls, from_station: str, to_station: str, date_str: str):
        try:
            url = "https://www.irctc.co.in"
            webbrowser.open(url)
            time.sleep(2.5)

            # 1. Dismiss language popup
            cls.select_language_popup("english")
            time.sleep(1.0)

            msg = f"IRCTC par {from_station} se {to_station} ke liye train search kar raha hoon."
            print(f"[WebAutomation] Sahayak: {msg}")
            TTSEngine.speak_async(msg)

            if pyautogui:
                cls._focus_browser_viewport()

                # 2. Fill 'From Station'
                pyautogui.press("tab")
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.write(from_station, interval=0.05)
                time.sleep(0.8)
                pyautogui.press("down")
                pyautogui.press("enter")
                time.sleep(0.3)

                # 3. Fill 'To Station'
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.write(to_station, interval=0.05)
                time.sleep(0.8)
                pyautogui.press("down")
                pyautogui.press("enter")
                time.sleep(0.3)

                # 4. Press Enter to submit search
                pyautogui.press("enter")

        except Exception as e:
            print(f"[WebAutomation Exception] IRCTC train search error: {e}")


    @classmethod
    def _focus_browser_viewport(cls):
        """Brings active browser window to OS foreground input focus."""
        if pyautogui:
            try:
                sw, sh = pyautogui.size()
                # Click upper center of viewport (y=250px) to activate window without clicking links
                pyautogui.click(sw // 2, 250)
                time.sleep(0.15)
            except Exception as e:
                print(f"[WebAutomation Warning] Focus browser failed: {e}")

    @classmethod
    def select_language_popup(cls, lang: str):
        """Selects Hindi or English language on IRCTC or similar web alert popups."""
        if pyautogui:
            try:
                sw, sh = pyautogui.size()
                lang_clean = lang.lower().strip()
                print(f"[WebAutomation] Selecting '{lang_clean}' language on popup...")

                # 1. Focus browser window
                cls._focus_browser_viewport()

                # 2. Keyboard DOM focus navigation on modal dialog
                pyautogui.press("tab")
                time.sleep(0.15)

                if "english" in lang_clean or "angrezi" in lang_clean or "eng" in lang_clean:
                    pyautogui.press("right")
                    time.sleep(0.15)
                    pyautogui.press("enter")
                    time.sleep(0.2)
                    
                    # Multi-point screen click fallback for English button (Right side of dialog)
                    target_x, target_y = sw // 2 + 60, sh // 2 + 120
                    for dx, dy in [(0, 0), (-10, 0), (10, 0), (0, 10), (0, -10)]:
                        pyautogui.click(target_x + dx, target_y + dy)
                        time.sleep(0.03)
                else:
                    pyautogui.press("enter")
                    time.sleep(0.2)
                    
                    # Multi-point screen click fallback for Hindi button (Left side of dialog)
                    target_x, target_y = sw // 2 - 60, sh // 2 + 120
                    for dx, dy in [(0, 0), (-10, 0), (10, 0), (0, 10), (0, -10)]:
                        pyautogui.click(target_x + dx, target_y + dy)
                        time.sleep(0.03)

                print(f"[WebAutomation] Language button '{lang_clean}' selected successfully.")
            except Exception as e:
                print(f"[WebAutomation Error] Select language failed: {e}")



    @classmethod
    def scroll_webpage(cls, direction: str = "down"):
        """Scrolls active browser page up or down."""
        if pyautogui:
            try:
                cls._focus_browser_viewport()
                if direction.lower() == "up":
                    print("[WebAutomation] Scrolling UP")
                    pyautogui.scroll(700)
                    pyautogui.press("pageup")
                else:
                    print("[WebAutomation] Scrolling DOWN")
                    pyautogui.scroll(-700)
                    pyautogui.press("pagedown")
            except Exception as e:
                print(f"[WebAutomation Error] Scroll failed: {e}")

    @classmethod
    def press_key(cls, key_name: str):
        """Presses a keyboard key on the active webpage (enter, tab, space, escape, etc.)."""
        if pyautogui and key_name:
            try:
                cls._focus_browser_viewport()
                clean_key = key_name.lower().strip()
                print(f"[WebAutomation] Pressing key: '{clean_key}'")
                pyautogui.press(clean_key)
            except Exception as e:
                print(f"[WebAutomation Error] Press key failed: {e}")

    @classmethod
    def fill_input_text(cls, text_to_type: str):
        """Simulates automated typing into the active browser input field."""
        if pyautogui and text_to_type:
            try:
                cls._focus_browser_viewport()
                print(f"[WebAutomation] Typing input into web form: '{text_to_type}'")
                pyautogui.write(text_to_type, interval=0.04)
                time.sleep(0.2)
                pyautogui.press("enter")
            except Exception as e:
                print(f"[WebAutomation Error] Typing failed: {e}")

    @classmethod
    def navigate_browser(cls, nav_action: str):
        """Performs browser navigation actions (back, refresh, close tab)."""
        if pyautogui:
            try:
                cls._focus_browser_viewport()
                nav = nav_action.lower().strip()
                if nav == "back":
                    print("[WebAutomation] Navigating Back")
                    pyautogui.hotkey("alt", "left")
                elif nav in ["refresh", "reload"]:
                    print("[WebAutomation] Refreshing Page")
                    pyautogui.hotkey("ctrl", "r")
                elif nav in ["close_tab", "close"]:
                    print("[WebAutomation] Closing Tab")
                    pyautogui.hotkey("ctrl", "w")
                elif nav == "zoom_in":
                    pyautogui.hotkey("ctrl", "plus")
                elif nav == "zoom_out":
                    pyautogui.hotkey("ctrl", "minus")
            except Exception as e:
                print(f"[WebAutomation Error] Navigation failed: {e}")

    @classmethod
    def click_screen(cls):
        """Simulates mouse click on active window/button."""
        if pyautogui:
            try:
                cls._focus_browser_viewport()
                print("[WebAutomation] Performing screen click")
                pyautogui.click()
            except Exception as e:
                print(f"[WebAutomation Error] Mouse click failed: {e}")


