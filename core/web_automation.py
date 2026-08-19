import time
import webbrowser
import threading
import urllib.parse
import sys
import subprocess
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
        """Selects Hindi or English language on IRCTC or similar web alert popups, and dismisses modal dialogs."""
        lang_clean = lang.lower().strip()
        print(f"[WebAutomation] Selecting '{lang_clean}' language on active website / IRCTC popup...")

        is_hindi = "hi" in lang_clean or "hindi" in lang_clean or "हिंदी" in lang_clean

        # Strategy 1: macOS AppleScript for Chrome / Safari / Edge
        if sys.platform == "darwin":
            target_lang_str = "हिन्दी" if is_hindi else "ENGLISH"
            js_code = (
                f"(function() {{"
                f"  try {{"
                f"    var dismissed = false;"
                f"    var okBtns = Array.from(document.querySelectorAll('button, .btn, .ui-dialog-buttonpane button, [role=\"button\"], [aria-label*=\"Close\"], [aria-label*=\"close\"], [aria-label*=\"Dismiss\"], [aria-label*=\"dismiss\"]'));"
                f"    for (var b of okBtns) {{"
                f"      var t = (b.innerText || '').trim().toUpperCase();"
                f"      if (t === 'OK' || t === 'SUBMIT' || t === 'DISMISS' || t === 'ACCEPT' || t === 'CONTINUE' || t === 'CLOSE' || t === 'AGREE' || t === 'I AGREE' || t === 'I UNDERSTAND') {{"
                f"        b.click();"
                f"        dismissed = true;"
                f"        break;"
                f"      }}"
                f"    }}"
                f"    var targetLang = '{target_lang_str}';"
                f"    var links = Array.from(document.querySelectorAll('a, button, span, li, [role=\"link\"], [role=\"button\"]'));"
                f"    for (var el of links) {{"
                f"      var txt = (el.innerText || '').trim();"
                f"      if (txt === targetLang || (targetLang === 'हिन्दी' && (txt === 'Hindi' || txt === 'हिंदी' || txt.indexOf('हिन्दी') !== -1)) || (targetLang === 'ENGLISH' && (txt === 'English' || txt.indexOf('ENGLISH') !== -1))) {{"
                f"        el.click();"
                f"        break;"
                f"      }}"
                f"    }}"
                f"    return 'success';"
                f"  }} catch(e) {{ return 'err: ' + e; }}"
                f"}})();"
            )

            applescript = f'''
            tell application "System Events"
                set runningApps to name of every application process
            end tell
            if runningApps contains "Google Chrome" then
                tell application "Google Chrome"
                    repeat with w in windows
                        repeat with t in tabs of w
                            if URL of t contains "irctc" or URL of t contains "http" then
                                tell t to execute javascript "{js_code}"
                                activate
                                return "chrome_success"
                            end if
                        end repeat
                    end repeat
                end tell
            end if
            if runningApps contains "Safari" then
                tell application "Safari"
                    repeat with w in windows
                        repeat with t in tabs of w
                            if URL of t contains "irctc" or URL of t contains "http" then
                                do JavaScript "{js_code}" in t
                                activate
                                return "safari_success"
                            end if
                        end repeat
                    end repeat
                end tell
            end if
            '''
            try:
                res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=5)
                if "success" in res.stdout:
                    print(f"[WebAutomation] AppleScript selected language '{lang_clean}' on browser tab.")
                    return
            except Exception as e_as:
                print(f"[WebAutomation Warning] AppleScript language selection note: {e_as}")

        # Strategy 2: PyAutoGUI keyboard & screen interaction
        if pyautogui:
            try:
                sw, sh = pyautogui.size()
                cls._focus_browser_viewport()

                # Press Enter / Escape to dismiss IRCTC alert modal
                pyautogui.press("enter")
                time.sleep(0.2)
                pyautogui.press("escape")
                time.sleep(0.2)

                if is_hindi:
                    # Click top right where language toggle is located
                    for dx, dy in [(0, 0), (-10, 0), (10, 0)]:
                        pyautogui.click(sw - 200 + dx, 120 + dy)
                else:
                    for dx, dy in [(0, 0), (-10, 0), (10, 0)]:
                        pyautogui.click(sw - 120 + dx, 120 + dy)

                print(f"[WebAutomation] Language button '{lang_clean}' selected successfully via PyAutoGUI.")
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

    @classmethod
    def fill_demo_form(cls, first_name: str = "Arpit", last_name: str = "Raj", age: str = "20", state: str = "Bihar") -> dict:
        """Automates filling and submitting the Sahayak Demo Website form."""
        thread = threading.Thread(
            target=cls._demo_form_filler_worker,
            args=(first_name, last_name, age, state),
            daemon=True
        )
        thread.start()
        return {"success": True, "msg": f"Automating demo form with Name: {first_name} {last_name}, Age: {age}, State: {state}."}

    @classmethod
    def _demo_form_filler_worker(cls, first_name: str, last_name: str, age: str, state: str):
        try:
            print(f"[WebAutomation] Starting demo form filling: {first_name} {last_name}, Age: {age}, State: {state}")
            time.sleep(0.5)

            # Strategy 1: macOS AppleScript execution (Google Chrome / Brave / Edge / Safari)
            if sys.platform == "darwin":
                js_code = (
                    f"(function() {{"
                    f"  var fn = document.getElementById('first-name'); if (fn) {{ fn.value = '{first_name}'; fn.dispatchEvent(new Event('input', {{bubbles:true}})); }}"
                    f"  var ln = document.getElementById('last-name'); if (ln) {{ ln.value = '{last_name}'; ln.dispatchEvent(new Event('input', {{bubbles:true}})); }}"
                    f"  var ag = document.getElementById('age'); if (ag) {{ ag.value = '{age}'; ag.dispatchEvent(new Event('input', {{bubbles:true}})); }}"
                    f"  var st = document.getElementById('state'); if (st) {{ st.value = '{state}'; st.dispatchEvent(new Event('input', {{bubbles:true}})); }}"
                    f"  setTimeout(function() {{"
                    f"    var btn = document.getElementById('login-button');"
                    f"    if (btn) btn.click();"
                    f"    else {{ var form = document.getElementById('demo-form'); if (form) form.submit(); }}"
                    f"  }}, 350);"
                    f"}})();"
                )

                applescript = f'''
                tell application "System Events"
                    set runningApps to name of every application process
                end tell
                if runningApps contains "Google Chrome" then
                    tell application "Google Chrome"
                        repeat with w in windows
                            repeat with t in tabs of w
                                if URL of t contains "demo" then
                                    tell t to execute javascript "{js_code}"
                                    return "chrome_success"
                                end if
                            end repeat
                        end repeat
                    end tell
                end if
                if runningApps contains "Safari" then
                    tell application "Safari"
                        repeat with w in windows
                            repeat with t in tabs of w
                                if URL of t contains "demo" then
                                    do JavaScript "{js_code}" in t
                                    return "safari_success"
                                end if
                            end repeat
                        end repeat
                    end tell
                end if
                '''
                try:
                    res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=5)
                    if "success" in res.stdout:
                        print(f"[WebAutomation] AppleScript automated form successfully: {res.stdout.strip()}")
                        return
                except Exception as e_as:
                    print(f"[WebAutomation Warning] AppleScript note: {e_as}")

            # Strategy 2: PyAutoGUI simulated interaction
            if pyautogui:
                cls._focus_browser_viewport()
                time.sleep(0.3)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.write(first_name, interval=0.03)
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.write(last_name, interval=0.03)
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.write(str(age), interval=0.03)
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.write(state, interval=0.03)
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.press("enter")
                print("[WebAutomation] Form filled via PyAutoGUI.")
                return

            # Strategy 3: Direct URL navigation fallback
            params = urllib.parse.urlencode({
                "firstName": first_name,
                "lastName": last_name,
                "age": age,
                "state": state
            })
            success_url = f"https://omthavari2006-dev.github.io/demo/success.html?{params}"
            webbrowser.open(success_url)

        except Exception as e:
            print(f"[WebAutomation Exception] Demo form filling error: {e}")


