import os
import threading
import tkinter as tk
from PIL import Image, ImageTk
from config import Config
from core.ai_engine import AIEngine
from core.speech_handler import ContinuousVoiceListenerWorker
from core.tts_engine import TTSEngine
from actions.action_runner import ActionRunner
from ui.settings_dialog import SettingsDialog

TRANSPARENT_COLOR = "#010101"

class SahayakOverlay(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Sahayak AI Mascot")
        self.geometry("220x270")

        # Make window frameless, always-on-top, and 100% background transparent
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg=TRANSPARENT_COLOR)
        try:
            self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except Exception as e:
            print(f"[UI Warning] Transparent color setting error: {e}")

        # Position at bottom-right corner of desktop screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(20, screen_width - 240)
        y = max(20, screen_height - 320)
        self.geometry(f"220x270+{x}+{y}")

        # Dragging & Typing variables
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._has_dragged = False
        self.is_typing_input_visible = False

        self.ai_engine = AIEngine()
        self.continuous_listener = None
        self.is_continuous_active = False

        self._load_mascot_images()
        self._build_mascot_ui()
        self.start_continuous_listening()

    def _load_mascot_images(self):
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        awake_path = os.path.join(assets_dir, "sahayak_robot.png")
        sleeping_path = os.path.join(assets_dir, "sahayak_sleeping.png")

        self.robot_awake_photo = None
        self.robot_sleeping_photo = None

        if os.path.exists(awake_path):
            try:
                img_awake = Image.open(awake_path).resize((180, 180), Image.Resampling.LANCZOS)
                self.robot_awake_photo = ImageTk.PhotoImage(img_awake)
            except Exception as e:
                print(f"[UI Warning] Error loading awake image: {e}")

        if os.path.exists(sleeping_path):
            try:
                img_sleeping = Image.open(sleeping_path).resize((180, 180), Image.Resampling.LANCZOS)
                self.robot_sleeping_photo = ImageTk.PhotoImage(img_sleeping)
            except Exception as e:
                print(f"[UI Warning] Error loading sleeping image: {e}")

    def set_standby_avatar(self):
        if hasattr(self, 'robot_sleeping_photo') and self.robot_sleeping_photo:
            self.avatar_lbl.config(image=self.robot_sleeping_photo)

    def set_awake_avatar(self):
        if hasattr(self, 'robot_awake_photo') and self.robot_awake_photo:
            self.avatar_lbl.config(image=self.robot_awake_photo)

    def _build_mascot_ui(self):
        # Container frame with transparent background
        self.container = tk.Frame(self, bg=TRANSPARENT_COLOR)
        self.container.pack(fill="both", expand=True)

        # 1. Floating Pixel-Art Robot Avatar Character (Defaults to Standby/Sleeping Avatar)
        initial_img = self.robot_sleeping_photo or self.robot_awake_photo
        if initial_img:
            self.avatar_lbl = tk.Label(self.container, image=initial_img, bg=TRANSPARENT_COLOR, cursor="hand2")
            self.avatar_lbl.pack(pady=(5, 0))
        else:
            self.avatar_lbl = tk.Label(self.container, text="🤖", font=("Segoe UI", 64), bg=TRANSPARENT_COLOR, fg="#00F0FF", cursor="hand2")
            self.avatar_lbl.pack(pady=10)

        # Enable dragging & clicking on the robot face
        self.avatar_lbl.bind("<Button-1>", self._start_drag)
        self.avatar_lbl.bind("<B1-Motion>", self._on_drag)
        self.avatar_lbl.bind("<ButtonRelease-1>", self._on_avatar_click_release)

        # Right-click context menu
        self.context_menu = tk.Menu(self, tearoff=0, bg="#1A1B29", fg="#F0F2FA", activebackground="#9D4EDD", activeforeground="#FFFFFF")
        self.context_menu.add_command(label="⚙️ Settings (Groq API Key)", command=self.open_settings)
        self.context_menu.add_command(label="⌨️ Toggle Typing Input (Testing)", command=self.toggle_typing_input)
        self.context_menu.add_command(label="⏯️ Pause/Resume Listening", command=self.toggle_continuous_listening)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✕ Exit Sahayak", command=self.on_close)

        self.avatar_lbl.bind("<Button-3>", self._show_context_menu)

        # 2. Sleek Floating Speech/Status Bubble under Robot
        self.bubble_frame = tk.Frame(self.container, bg="#1A1B29", highlightbackground="#00F0FF", highlightthickness=1)
        self.bubble_frame.pack(fill="x", padx=10, pady=(2, 0))

        self.status_lbl = tk.Label(
            self.bubble_frame,
            text="🟢 Say 'Sahayak'...",
            font=("Segoe UI", 8, "bold"),
            fg="#00F0FF",
            bg="#1A1B29",
            wraplength=180,
            justify="center"
        )
        self.status_lbl.pack(padx=6, pady=4)

        # 3. [TESTING MODULE] Interactive Text Typing Input Box (Hidden by default, toggleable on face click)
        self.input_frame = tk.Frame(self.container, bg="#1A1B29", highlightbackground="#9D4EDD", highlightthickness=1)
        
        self.cmd_entry = tk.Entry(
            self.input_frame,
            bg="#0E0F19",
            fg="#FFFFFF",
            insertbackground="#00F0FF",
            font=("Segoe UI", 9),
            relief="flat"
        )
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(5, 2), pady=3)
        self.cmd_entry.bind("<Return>", self._submit_typed_command)

        self.send_btn = tk.Button(
            self.input_frame,
            text="➔",
            bg="#9D4EDD",
            fg="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            activebackground="#C77DFF",
            activeforeground="#FFFFFF",
            cursor="hand2",
            command=self._submit_typed_command
        )
        self.send_btn.pack(side="right", padx=(0, 4), pady=3)

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._has_dragged = False

    def _on_drag(self, event):
        dx = abs(event.x - self._drag_start_x)
        dy = abs(event.y - self._drag_start_y)
        if dx > 3 or dy > 3:
            self._has_dragged = True
            x = self.winfo_x() + (event.x - self._drag_start_x)
            y = self.winfo_y() + (event.y - self._drag_start_y)
            self.geometry(f"+{x}+{y}")

    def _on_avatar_click_release(self, event):
        if not self._has_dragged:
            self.toggle_typing_input()

    def toggle_typing_input(self):
        """Toggles typing input frame visibility for testing."""
        curr_x = self.winfo_x()
        curr_y = self.winfo_y()

        if self.is_typing_input_visible:
            self.input_frame.pack_forget()
            self.is_typing_input_visible = False
            self.geometry(f"220x270+{curr_x}+{curr_y}")
        else:
            self.input_frame.pack(fill="x", padx=10, pady=(4, 0))
            self.is_typing_input_visible = True
            self.geometry(f"220x310+{curr_x}+{curr_y}")
            self.cmd_entry.focus_set()

    def _submit_typed_command(self, event=None):
        text = self.cmd_entry.get().strip()
        if text:
            self.cmd_entry.delete(0, tk.END)
            print(f"[Testing Typing Input] Submitting: '{text}'")
            self._process_recognized_text(text, text)

    def _show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def open_settings(self):
        SettingsDialog(self)

    def start_continuous_listening(self):
        if not self.continuous_listener:
            self.continuous_listener = ContinuousVoiceListenerWorker(
                on_command_detected=self._on_wake_word_command,
                on_stop_command=self._on_stop_command,
                on_listening_state_change=self._on_listening_state_change
            )
        self.continuous_listener.start()
        self.is_continuous_active = True
        self.status_lbl.config(text="🟢 Say 'Sahayak'...", fg="#00F0FF")
        self.set_standby_avatar()

    def stop_continuous_listening(self):
        if self.continuous_listener:
            self.continuous_listener.stop()
        self.is_continuous_active = False
        self.status_lbl.config(text="🔴 Mic Paused", fg="#FF5252")

    def toggle_continuous_listening(self):
        if self.is_continuous_active:
            self.stop_continuous_listening()
        else:
            self.start_continuous_listening()

    def _on_listening_state_change(self, state_text):
        if self.is_continuous_active:
            if "Active" in state_text:
                color = "#00E676"
                self.after(0, lambda: self.set_awake_avatar())
            else:
                color = "#00F0FF"
                self.after(0, lambda: self.set_standby_avatar())
            self.after(0, lambda: self.status_lbl.config(text=f"{state_text[:22]}", fg=color))

    def _on_wake_word_command(self, full_transcript, command_text):
        self.after(0, lambda: self.set_awake_avatar())
        self.after(0, lambda: self._process_recognized_text(command_text, full_transcript))

    def _on_stop_command(self, transcript):
        self.after(0, lambda: self._handle_stop())

    def _handle_stop(self):
        TTSEngine.stop()
        self.ai_engine.reset_history()
        self.set_standby_avatar()
        self.status_lbl.config(text="🛑 Standby (Say 'Sahayak')", fg="#9499B8")
        TTSEngine.speak_async("Shifting on standby mode.")




    def _process_recognized_text(self, user_command, full_transcript=""):
        display_text = user_command if user_command else full_transcript
        self.status_lbl.config(text=f"⚡ Heard: '{display_text[:18]}...'", fg="#00E676")

        threading.Thread(target=self._ai_worker, args=(display_text,), daemon=True).start()

    def _ai_worker(self, user_text):
        result = self.ai_engine.process_query(user_text)
        reply = result.get("reply", "No response.")
        action = result.get("action", {"type": "none", "params": {}})

        # Show AI reply in speech bubble
        self.after(0, lambda: self.status_lbl.config(text=reply[:30] + ("..." if len(reply) > 30 else ""), fg="#00F0FF"))

        # Speak reply out loud asynchronously in user's language
        TTSEngine.speak_async(reply)

        # Execute Action
        ActionRunner.execute(action.get("type", "none"), action.get("params", {}))

    def on_close(self):
        self.stop_continuous_listening()
        self.destroy()
