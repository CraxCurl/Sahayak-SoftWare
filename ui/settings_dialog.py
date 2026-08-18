import tkinter as tk
from tkinter import ttk, messagebox
from config import Config
from ui.styles import BG_DARK, BG_CARD, ACCENT_CYAN, TEXT_LIGHT, TEXT_MUTED, BORDER_COLOR, FONT_BODY, FONT_TITLE

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sahayak Settings")
        self.geometry("450x240")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.winfo_screenheight() // 2) - (240 // 2)
        self.geometry(f"450x240+{x}+{y}")

        # Title Label
        title_lbl = tk.Label(self, text="⚙️ Configure Groq API Key", font=FONT_TITLE, fg=ACCENT_CYAN, bg=BG_DARK)
        title_lbl.pack(anchor="w", padx=20, pady=(15, 5))

        desc_lbl = tk.Label(
            self,
            text="Get a free key from console.groq.com to enable Whisper STT & Llama 3.3",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=BG_DARK,
            wraplength=400,
            justify="left"
        )
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        # API Key Input
        key_frame = tk.Frame(self, bg=BG_DARK)
        key_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(key_frame, text="GROQ_API_KEY:", font=FONT_BODY, fg=TEXT_LIGHT, bg=BG_DARK).pack(anchor="w")

        self.key_entry = tk.Entry(
            key_frame,
            font=("Consolas", 10),
            bg=BG_CARD,
            fg=ACCENT_CYAN,
            insertbackground=TEXT_LIGHT,
            relief="solid",
            bd=1,
            show="*"
        )
        self.key_entry.pack(fill="x", pady=5, ipady=4)

        # Load existing key
        existing_key = Config.get_api_key()
        if existing_key:
            self.key_entry.insert(0, existing_key)

        # Buttons Frame
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=20, pady=20)

        save_btn = tk.Button(
            btn_frame,
            text="💾 Save Key",
            font=FONT_BODY,
            bg=ACCENT_CYAN,
            fg=BG_DARK,
            activebackground="#00C8D6",
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.save_key
        )
        save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=FONT_BODY,
            bg=BG_CARD,
            fg=TEXT_LIGHT,
            activebackground=BORDER_COLOR,
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        cancel_btn.pack(side="right")

    def save_key(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Empty Key", "Please enter a valid GROQ API Key.")
            return
        Config.save_api_key(key)
        messagebox.showinfo("Success", "GROQ API Key saved successfully to .env!")
        self.destroy()
