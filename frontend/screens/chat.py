# frontend/screens/chat.py
import customtkinter as ctk
import threading
import requests
import uuid
import qrcode
import re
import time
import queue

from frontend.config import *
from frontend.assets import assets

try:
    from src.services.audio_client import AudioClient
except ImportError:
    print("Warning: AudioClient not found")
    class AudioClient: 
        def __init__(self, **kw): pass
        def speak(self, *a, **kw): pass
        def listen(self, *a, **kw): return None

# =========================
# Mini Telex (gọn + chuẩn)
# =========================
TONE_KEYS = {"s": 1, "f": 2, "r": 3, "x": 4, "j": 5}

_VOWELS = {
    "a": ["a", "á", "à", "ả", "ã", "ạ"],
    "ă": ["ă", "ắ", "ằ", "ẳ", "ẵ", "ặ"],
    "â": ["â", "ấ", "ầ", "ẩ", "ẫ", "ậ"],
    "e": ["e", "é", "è", "ẻ", "ẽ", "ẹ"],
    "ê": ["ê", "ế", "ề", "ể", "ễ", "ệ"],
    "i": ["i", "í", "ì", "ỉ", "ĩ", "ị"],
    "o": ["o", "ó", "ò", "ỏ", "õ", "ọ"],
    "ô": ["ô", "ố", "ồ", "ổ", "ỗ", "ộ"],
    "ơ": ["ơ", "ớ", "ờ", "ở", "ỡ", "ợ"],
    "u": ["u", "ú", "ù", "ủ", "ũ", "ụ"],
    "ư": ["ư", "ứ", "ừ", "ử", "ữ", "ự"],
    "y": ["y", "ý", "ỳ", "ỷ", "ỹ", "ỵ"],
}

_BASE_BY_CHAR = {}
_FORMS_BY_BASE = {}
for base, forms in _VOWELS.items():
    _FORMS_BY_BASE[base] = forms
    _FORMS_BY_BASE[base.upper()] = [c.upper() for c in forms]
    for c in forms:
        _BASE_BY_CHAR[c] = base
        _BASE_BY_CHAR[c.upper()] = base.upper()

_PRIORITY_BASES = set(list("âăêôơưÂĂÊÔƠƯ"))

class ChatScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller 

        self.session_id = str(uuid.uuid4())
        self.audio_client = AudioClient(tts_url=TTS_URL)
        
        self.chat_history = []
        self.message_labels = []
        self.stop_requested = False
        self.current_ai_container = None
        
        # --- TTS Streaming Queue ---
        self.tts_queue = queue.Queue()
        self.stop_tts = False

        self.current_state = None   
        self.anim_job = None
        self.anim_frame_idx = 0

        # --- NEW: Track playing state ---
        self.current_playing_btn = None
        self.current_playing_text = None
        
        # --- Keyboard State ---
        self.vkbd_frame = None
        self.vkbd_keys = []
        self.telex_enabled = True
        self.vkbd_shift = True          # bắt đầu in hoa
        self.shift_oneshot = True       # auto-off sau 1 chữ cái
        self.caps_locked = False        # double-tap Shift = caps lock
        self._last_shift_tap = 0.0
        self._double_tap_window = 0.38  # giây
        
        # --- Avatar Cache ---
        self._avatar_cache = {}
        self._resize_job = None
        self.CHAT_WRAP_MAX = 460
        self.keyboard_visible = False
        
        self._build_layout()
        
        self.set_avatar_state("waving", play_once=True)
        
        # Câu chào mặc định
        self.add_chat_bubble("ai", "Xin chào! Tôi có thể giúp gì cho bạn hôm nay?")

        # --- GLOBAL CLICK BINDING FOR KEYBOARD HIDE ---
        self.controller.bind_all("<Button-1>", self._on_global_click, add="+")
        self.controller.bind("<Configure>", self._on_window_resize, add="+")

    def _on_global_click(self, event):
        """
        Hide keyboard if user clicks anywhere OUTSIDE the keyboard frame and the entry.
        """
        try:
            # If keyboard is not visible, do nothing
            if not self.vkbd_frame or not self.keyboard_visible:
                return

            # Get the widget that was clicked
            clicked_widget = event.widget

            # Check if clicked widget is the Entry or part of Keyboard
            # We check if the widget str path starts with the keyboard frame's path
            # or is the entry itself.
            vkbd_path = str(self.vkbd_frame)
            entry_path = str(self.entry)
            widget_path = str(clicked_widget)

            if widget_path.startswith(vkbd_path):
                return # Clicked inside keyboard
            
            if widget_path == entry_path or widget_path.startswith(entry_path):
                return # Clicked on input box (or its internal parts)

            # If we are here, we clicked outside -> Hide
            self.hide_keyboard()
            
        except Exception as e:
            # print(f"Global click error: {e}")
            pass

    def _on_window_resize(self, event=None):
        try:
            if self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(120, self._apply_layout_policy)
        except Exception:
            pass

    def _compute_avatar_size(self):
        return (300, 350)

    def _reflow_layout(self):
        try:
            wrap = max(260, self.chat_card.winfo_width() - 80)
            for lbl in getattr(self, "message_labels", []):
                try:
                    # Clamp to CHAT_WRAP_MAX to avoid overflow on Pi
                    lbl.configure(wraplength=min(self.CHAT_WRAP_MAX, wrap))
                except Exception:
                    pass
            # Reassert input container min height and column minsizes
            try:
                if self.input_container:
                    self.input_container.configure(height=70)
                if self.input_bg:
                    self.input_bg.grid_columnconfigure(1, minsize=48)
                    self.input_bg.grid_columnconfigure(2, minsize=48)
            except Exception:
                pass
            # Keyboard slot keeps layout stable; nothing to reposition
        except Exception:
            pass

    def _refresh_ui(self):
        try:
            wrap = self._bubble_wrap_length()
            for lbl in getattr(self, "message_labels", []):
                try:
                    lbl.configure(wraplength=wrap)
                except Exception:
                    pass
            self.chat_frame.update_idletasks()
        except Exception:
            pass

    def _apply_layout_policy(self):
        try:
            # Update bubble wraplength
            wrap = self._bubble_wrap_length()
            for lbl in getattr(self, "message_labels", []):
                try:
                    lbl.configure(wraplength=wrap)
                except Exception:
                    pass

            # Reassert input container and buttons sizing
            if self.input_container:
                self.input_container.configure(height=70)
            if self.input_bg:
                self.input_bg.grid_rowconfigure(0, minsize=36)
                self.input_bg.grid_columnconfigure(0, weight=1)
                self.input_bg.grid_columnconfigure(1, minsize=48)
                self.input_bg.grid_columnconfigure(2, minsize=48)

            # Keep keyboard slot sizing stable
            if self.keyboard_slot:
                self.keyboard_slot.grid_columnconfigure(0, weight=1)
                if self.keyboard_visible:
                    self.keyboard_slot.configure(height=220)
                    if self.vkbd_frame:
                        try:
                            self.vkbd_frame.grid_configure(sticky="ew", padx=10, pady=(6, 10))
                        except Exception:
                            pass
                else:
                    self.keyboard_slot.configure(height=0)

            self.update_idletasks()
        except Exception:
            pass

    def _bubble_wrap_length(self):
        try:
            w = max(260, self.chat_card.winfo_width() - 80)
            return min(self.CHAT_WRAP_MAX, w)
        except Exception:
            return self.CHAT_WRAP_MAX

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0) # Cột Avatar
        self.grid_columnconfigure(1, weight=1) # Cột Chat
        self.grid_rowconfigure(0, weight=1)

        # === 1. AVATAR FRAME (TRÁI) ===
        # Professional Look: No border, just clean white card
        self.ava_frame = ctk.CTkFrame(
            self, 
            fg_color=CARD_BG,
            corner_radius=0, 
            width=420
        )
        self.ava_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.ava_frame.grid_propagate(False)
        self.ava_frame.pack_propagate(False) # Fix: Ensure frame respects width with packed children

        # Avatar Label
        # Use a resized placeholder initially, actual images handled by set_avatar_state
        self.avatar_label = ctk.CTkLabel(self.ava_frame, text="", image=None) 
        self.avatar_label.pack(expand=True, fill="both", padx=20, pady=10)

        # === 2. CHAT PANEL (PHẢI) ===
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=0)
        self.right_panel.grid_rowconfigure(3, weight=0)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Header (Minimalist)
        header = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # Title
        ctk.CTkLabel(
            header, 
            text="Trợ lý Ảo AI Banking", 
            font=(FONT_FAMILY, 24, "bold"), 
            text_color=PRIMARY
        ).pack(side="left", anchor="s")

        # End Button (Pill shape)
        ctk.CTkButton(
            header, 
            text="Kết thúc phiên", 
            width=120, 
            height=36,
            fg_color=DANGER, 
            hover_color="#B91C1C",
            corner_radius=18,
            font=(FONT_FAMILY, 14, "bold"),
            command=self.controller.show_welcome
        ).pack(side="right", anchor="s")

        # Chat Area (Clean Card)
        self.chat_card = ctk.CTkFrame(
            self.right_panel, 
            fg_color=CARD_BG, 
            corner_radius=20,
            border_width=1, 
            border_color=BORDER_COLOR
        )
        self.chat_card.grid(row=1, column=0, sticky="nsew")
        # Global click handler handles this now, specific bindings removed to avoid conflicts
        
        self.chat_frame = ctk.CTkScrollableFrame(
            self.chat_card, 
            fg_color="transparent", 
            label_text=""
        )
        self.chat_frame.pack(expand=True, fill="both", padx=15, pady=15)
        # Global click handler handles this now
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.chat_card, 
            text="", 
            font=(FONT_FAMILY, 13, "italic"), 
            text_color=MUTED
        )
        self.status_label.pack(anchor="w", padx=25, pady=(0, 10))

        # Input Area (Floating Pill)
        self.input_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.input_container.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        self.input_container.grid_columnconfigure(0, weight=1)
        self.input_container.configure(height=70)
        self.input_container.grid_propagate(False)
        
        # Reserved slot for keyboard to avoid layout jump
        self.keyboard_slot = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=0)
        self.keyboard_slot.grid(row=3, column=0, sticky="ew")
        self.keyboard_slot.grid_columnconfigure(0, weight=1)
        self.keyboard_slot.grid_propagate(False)

        self.input_bg = ctk.CTkFrame(
            self.input_container, 
            fg_color=CARD_BG, 
            corner_radius=30, 
            border_width=1, 
            border_color=PRIMARY
        )
        self.input_bg.grid(row=0, column=0, sticky="ew")
        self.input_bg.grid_columnconfigure(0, weight=1)
        self.input_bg.grid_columnconfigure(1, minsize=48)
        self.input_bg.grid_columnconfigure(2, minsize=48)

        self.entry = ctk.CTkEntry(
            self.input_bg, 
            placeholder_text="Nhập câu hỏi của bạn...", 
            font=(FONT_FAMILY, 16), 
            height=45, 
            border_width=0, 
            fg_color="transparent",
            text_color=TEXT_COLOR_DARK,
            placeholder_text_color=MUTED
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=20)
        self.entry.bind("<Return>", self.on_send)
        self.entry.bind("<Key>", self.controller.reset_timer)
        self.entry.bind("<Button-1>", lambda e: self.show_keyboard())

        # Buttons
        self.btn_mic = ctk.CTkButton(
            self.input_bg, 
            image=assets.icons["mic"], 
            text="", 
            width=42, 
            height=42, 
            corner_radius=21, 
            fg_color=ACCENT, 
            hover_color="#0284C7",
            command=self.on_mic
        )
        self.btn_mic.grid(row=0, column=1, padx=(5, 5), pady=4)

        self.btn_send = ctk.CTkButton(
            self.input_bg, 
            image=assets.icons["send"], 
            text="", 
            width=42, 
            height=42, 
            corner_radius=21, 
            fg_color="#10B981", # Emerald Green
            hover_color="#059669",
            command=self.on_send
        )
        self.btn_send.grid(row=0, column=2, padx=(5, 10), pady=4)

        # === 3. VIRTUAL KEYBOARD ===
        self.create_virtual_keyboard()

    # =========================
    # Virtual Keyboard Logic
    # =========================
    def apply_shift_style(self):
        try:
            if not getattr(self, "shift_btn", None):
                return
            if self.caps_locked:
                self.shift_btn.configure(fg_color=CAPS_COLOR, text_color="#ffffff")
            elif self.vkbd_shift:
                self.shift_btn.configure(fg_color=PRIMARY, text_color="#ffffff")
            else:
                self.shift_btn.configure(fg_color=KEY_BG, text_color=TEXT_COLOR_DARK)
        except Exception:
            pass

    def update_key_labels(self):
        try:
            upper = self.caps_locked or self.vkbd_shift
            for btn in self.vkbd_keys:
                txt = btn.cget("text")
                if len(txt) == 1 and txt.isalpha():
                    btn.configure(text=(txt.upper() if upper else txt.lower()))
        except Exception:
            pass

    def create_virtual_keyboard(self):
        try:
            if self.vkbd_frame and self.vkbd_frame.winfo_exists():
                self.vkbd_frame.destroy()
        except Exception:
            pass

        self.vkbd_keys = []

        # Container for keyboard inside reserved slot (stable grid)
        self.vkbd_frame = ctk.CTkFrame(
            self.keyboard_slot,
            fg_color=KEYBOARD_BG, 
            corner_radius=15
        )
        # Initially hidden: will be gridded on demand

        rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

        # Row 1-3
        for r in rows:
            rowf = ctk.CTkFrame(self.vkbd_frame, fg_color="transparent")
            rowf.pack(fill="x", pady=4)
            rowf_inner = ctk.CTkFrame(rowf, fg_color="transparent")
            rowf_inner.pack(anchor="center")
            for ch in r:
                btn = ctk.CTkButton(
                    rowf_inner, 
                    text=ch, 
                    width=55, 
                    height=50,
                    corner_radius=8,
                    fg_color=KEY_BG,
                    text_color=KEY_TEXT,
                    font=(FONT_FAMILY, 18),
                    hover_color="#E2E8F0",
                    command=lambda c=ch: self.virtual_key_press(c)
                )
                btn.pack(side="left", padx=3)
                self.vkbd_keys.append(btn)

        # Control Row
        ctrl_row = ctk.CTkFrame(self.vkbd_frame, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(4, 10))
        ctrl_row_inner = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        ctrl_row_inner.pack(anchor="center")

        # Shift
        self.shift_btn = ctk.CTkButton(
            ctrl_row_inner, 
            text="⇧", 
            width=70, 
            height=50,
            corner_radius=8,
            font=(FONT_FAMILY, 18, "bold"),
            command=self.toggle_shift
        )
        self.shift_btn.pack(side="left", padx=3)

        # Space
        space_btn = ctk.CTkButton(
            ctrl_row_inner, 
            text="Space", 
            width=300, 
            height=50,
            corner_radius=8,
            fg_color=KEY_BG,
            text_color=KEY_TEXT,
            hover_color="#E2E8F0",
            command=lambda: self.virtual_key_press(" ")
        )
        space_btn.pack(side="left", padx=3)

        # Backspace
        back_btn = ctk.CTkButton(
            ctrl_row_inner, 
            text="⌫", 
            width=70, 
            height=50,
            corner_radius=8,
            fg_color=KEY_BG,
            text_color=KEY_TEXT,
            hover_color="#FECACA", # Light Red Hover
            command=self.virtual_backspace
        )
        back_btn.pack(side="left", padx=3)

        # Enter
        enter_btn = ctk.CTkButton(
            ctrl_row_inner, 
            text="↵", 
            width=70, 
            height=50,
            corner_radius=8,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            command=self.on_send
        )
        enter_btn.pack(side="left", padx=3)

        # VN/EN button
        lang_text = "VN" if self.telex_enabled else "EN"
        is_vn = self.telex_enabled
        self.lang_btn = ctk.CTkButton(
            ctrl_row_inner,
            text=lang_text,
            width=60,
            height=50,
            corner_radius=8,
            command=self.toggle_language,
            fg_color=PRIMARY if is_vn else KEY_BG,
            text_color="#ffffff" if is_vn else KEY_TEXT,
            font=(FONT_FAMILY, 14, "bold")
        )
        self.lang_btn.pack(side="left", padx=3)

        # Hide Keyboard Button
        hide_btn = ctk.CTkButton(
            ctrl_row_inner,
            text="▼",
            width=50,
            height=50,
            corner_radius=8,
            fg_color=MUTED,
            hover_color="#475569",
            command=self.hide_keyboard
        )
        hide_btn.pack(side="left", padx=3)

        self.apply_shift_style()
        self.update_key_labels()

    def show_keyboard(self):
        try:
            if self.vkbd_frame and not self.keyboard_visible:
                self.keyboard_slot.configure(height=220)
                self.vkbd_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 10))
                self.keyboard_visible = True
                self.update_idletasks()
                self.scroll_bottom()
                self.after(0, self._apply_layout_policy)
        except Exception:
            pass

    def hide_keyboard(self):
        try:
            if self.vkbd_frame and self.keyboard_visible:
                self.vkbd_frame.grid_remove()
                self.keyboard_slot.configure(height=0)
                self.keyboard_visible = False
                self.update_idletasks()
                self.after(0, self._apply_layout_policy)
        except Exception:
            pass

    # reserved: keyboard positioning handled by keyboard_slot

    def toggle_shift(self):
        self.controller.reset_timer()
        now = time.monotonic()
        dt = now - self._last_shift_tap
        self._last_shift_tap = now

        # nếu đang caps, tap 1 lần để tắt caps và về oneshot
        if self.caps_locked and dt > self._double_tap_window:
            self.caps_locked = False
            self.vkbd_shift = True
            self.shift_oneshot = True
            self.apply_shift_style()
            self.update_key_labels()
            return

        # double tap => toggle caps
        if dt <= self._double_tap_window:
            self.caps_locked = not self.caps_locked
            if self.caps_locked:
                self.vkbd_shift = True
                self.shift_oneshot = False
            else:
                self.vkbd_shift = True
                self.shift_oneshot = True
            self.apply_shift_style()
            self.update_key_labels()
            return

        # single tap (normal) => toggle one-shot shift
        if not self.caps_locked:
            self.vkbd_shift = not self.vkbd_shift
            self.shift_oneshot = True if self.vkbd_shift else False
            self.apply_shift_style()
            self.update_key_labels()

    def toggle_language(self):
        self.controller.reset_timer()
        self.telex_enabled = not self.telex_enabled
        is_vn = self.telex_enabled

        try:
            if self.lang_btn:
                self.lang_btn.configure(
                    text=("VN" if is_vn else "EN"),
                    fg_color=(PRIMARY if is_vn else KEY_BG),
                    text_color=("#ffffff" if is_vn else KEY_TEXT),
                )
        except Exception:
            pass

        try:
            placeholder = "Nhập tin nhắn..." if is_vn else "Type a message..."
            self.entry.configure(placeholder_text=placeholder)
        except Exception:
            pass

    def _maybe_auto_shift_on(self, last_char: str):
        if self.caps_locked:
            return
        if last_char in (".", "!", "?", "\n"):
            self.vkbd_shift = True
            self.shift_oneshot = True
            self.apply_shift_style()
            self.update_key_labels()

    def virtual_key_press(self, char: str):
        self.controller.reset_timer()
        try:
            is_letter = char.isalpha()

            upper = self.caps_locked or self.vkbd_shift
            if is_letter:
                c = char.upper() if upper else char.lower()
            else:
                c = char

            if self.telex_enabled and is_letter:
                self.process_telex_input(c)
            else:
                cur = self.entry.get()
                idx = self.entry.index("insert")
                new = cur[:idx] + c + cur[idx:]
                self.entry.delete(0, "end")
                self.entry.insert(0, new)
                try:
                    self.entry.icursor(idx + len(c))
                except Exception:
                    pass

            # auto-off oneshot after 1 letter (if not caps)
            if is_letter and (not self.caps_locked) and self.vkbd_shift and self.shift_oneshot:
                self.vkbd_shift = False
                self.shift_oneshot = False
                self.apply_shift_style()
                self.update_key_labels()
                return

            # punctuation => maybe auto-shift-on (if not caps)
            if not is_letter and c:
                self._maybe_auto_shift_on(c)

        except Exception as e:
            print(f"VKbd error: {e}")

    def process_telex_input(self, char: str):
        try:
            cur = self.entry.get()
            idx = self.entry.index("insert")
            before, after = cur[:idx], cur[idx:]
            key = char.lower()

            def set_text(new_before: str):
                new = new_before + after
                self.entry.delete(0, "end")
                self.entry.insert(0, new)
                try:
                    self.entry.icursor(len(new_before))
                except Exception:
                    pass

            # dd -> đ
            if key == "d" and before and before[-1] in ("d", "D"):
                set_text(before[:-1] + ("Đ" if before[-1] == "D" else "đ"))
                return

            # aa/ee/oo ; aw/ow/uw
            if before:
                prev = before[-1]
                prev_low = prev.lower()
                if key == "a" and prev_low == "a":
                    set_text(before[:-1] + ("Â" if prev.isupper() else "â"))
                    return
                if key == "e" and prev_low == "e":
                    set_text(before[:-1] + ("Ê" if prev.isupper() else "ê"))
                    return
                if key == "o" and prev_low == "o":
                    set_text(before[:-1] + ("Ô" if prev.isupper() else "ô"))
                    return
                if key == "w":
                    if prev_low == "a":
                        set_text(before[:-1] + ("Ă" if prev.isupper() else "ă"))
                        return
                    if prev_low == "o":
                        set_text(before[:-1] + ("Ơ" if prev.isupper() else "ơ"))
                        return
                    if prev_low == "u":
                        set_text(before[:-1] + ("Ư" if prev.isupper() else "ư"))
                        return

            # tone keys
            if key in TONE_KEYS:
                j = len(before)
                i = j
                while i > 0 and before[i - 1].isalpha():
                    i -= 1
                word = before[i:j]
                if not word:
                    set_text(before + char)
                    return

                vowels = []
                for pos, ch in enumerate(word):
                    base = _BASE_BY_CHAR.get(ch)
                    if base and base.lower() in _VOWELS:
                        vowels.append(pos)

                if not vowels:
                    set_text(before + char)
                    return

                wl = word.lower()

                def is_qu(pos): return pos == 1 and len(wl) >= 2 and wl[0] == "q" and wl[1] == "u"
                def is_gi(pos): return pos == 1 and len(wl) >= 2 and wl[0] == "g" and wl[1] == "i"

                vowels2 = [p for p in vowels if not (is_qu(p) or is_gi(p))]
                if vowels2:
                    vowels = vowels2

                target = None
                for p in vowels:
                    if _BASE_BY_CHAR.get(word[p]) in _PRIORITY_BASES:
                        target = p
                if target is None:
                    last_base = _BASE_BY_CHAR.get(word[vowels[-1]], "").lower()
                    if len(vowels) >= 2 and last_base in ("i", "y", "u"):
                        target = vowels[-2]
                    else:
                        target = vowels[-1]

                ch = word[target]
                base = _BASE_BY_CHAR.get(ch, ch)
                forms = _FORMS_BY_BASE.get(base)
                if not forms:
                    set_text(before + char)
                    return

                new_ch = forms[TONE_KEYS[key]]
                new_word = word[:target] + new_ch + word[target + 1:]
                set_text(before[:i] + new_word)
                return

            set_text(before + char)

        except Exception as e:
            print(f"Telex error: {e}")

    def virtual_backspace(self):
        self.controller.reset_timer()
        try:
            cur = self.entry.get()
            idx = self.entry.index("insert")
            if idx == 0:
                if cur == "" and not self.caps_locked:
                    self.vkbd_shift = True
                    self.shift_oneshot = True
                    self.apply_shift_style()
                    self.update_key_labels()
                return

            new = cur[:max(0, idx - 1)] + cur[idx:]
            self.entry.delete(0, "end")
            self.entry.insert(0, new)
            try:
                self.entry.icursor(idx - 1)
            except Exception:
                pass

            if new == "" and not self.caps_locked:
                self.vkbd_shift = True
                self.shift_oneshot = True
                self.apply_shift_style()
                self.update_key_labels()

        except Exception as e:
            print(f"VKbd backspace error: {e}")

    # --- LOGIC AVATAR ---
    # Trong class ChatScreen

    def _get_resized_frames(self, state):
        """
        Resize avatar frames to fit 340px width (approx 300x330).
        Cache results to avoid lag.
        """
        if state in self._avatar_cache:
            return self._avatar_cache[state]

        # 1. Get original frames
        # Handle _anim logic here to simplify set_avatar_state
        raw = assets.avatars.get(f"{state}_anim") or assets.avatars.get(state)
        
        if not raw:
            return None

        TARGET_SIZE = self._compute_avatar_size()

        def resize_one(img_obj):
            try:
                # Access internal PIL image and create new CTkImage
                # Note: This relies on CTkImage implementation detail (_light_image)
                if hasattr(img_obj, "_light_image"):
                     return ctk.CTkImage(light_image=img_obj._light_image, size=TARGET_SIZE)
                return img_obj # Fallback
            except:
                return img_obj

        # 2. Resize
        if isinstance(raw, list):
            resized = [resize_one(img) for img in raw]
        else:
            resized = resize_one(raw)

        # 3. Cache
        self._avatar_cache[state] = resized
        return resized

    def set_avatar_state(self, state, play_once=False):
        """
        state: 'normal', 'listening', 'thinking', 'answering', 'waving'
        play_once: True (Chạy hết list ảnh rồi về normal), False (Lặp vô tận)
        """
        # Nếu đang là trạng thái đó rồi thì bỏ qua (trừ khi ép chạy play_once)
        if self.current_state == state and not play_once: return
        
        self.current_state = state

        # Hủy animation cũ nếu đang chạy
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None

        # 1. Tìm ảnh (Đã resize)
        frames = self._get_resized_frames(state)

        # 2. Nếu là List ảnh -> Chạy Animation
        if frames and isinstance(frames, list) and len(frames) > 0:
            self.anim_frame_idx = 0
            # delay=60ms (~15 FPS) là tốc độ vừa phải cho Anime
            self._animate_loop(frames, delay=60, play_once=play_once)
        
        # 3. Nếu là Ảnh đơn -> Hiển thị tĩnh
        else:
            # Fallback về normal nếu không tìm thấy ảnh
            if not frames: 
                frames = self._get_resized_frames("normal")
            
            # Xử lý trường hợp list chỉ có 1 ảnh
            img = frames if not isinstance(frames, list) else frames[0]
            
            if img:
                self.avatar_label.configure(image=img)
    
    def _animate_loop(self, frames, delay, play_once):
        # 1. Kiểm tra an toàn
        if play_once and self.current_state != "waving": return 
        if not play_once and self.current_state not in ["answering", "speaking"]: return

        # 2. Hiển thị khung hình hiện tại
        if self.anim_frame_idx < len(frames):
            self.avatar_label.configure(image=frames[self.anim_frame_idx])
            
            # --- LOGIC ĐIỀU KHIỂN VÒNG LẶP ---
            
            # Kiểm tra cả 2 tên cho chắc chắn
            if self.current_state in ["answering", "speaking"]:
                self.anim_frame_idx += 1
                
                # CẤU HÌNH (Dựa theo yêu cầu của bạn: Ảnh 9 -> 24)
                # Index = Số thứ tự ảnh - 1
                LOOP_START = 7   # Ảnh số 8
                LOOP_END   = 22  # Ảnh số 23
                
                # [DEBUG] Bỏ comment dòng dưới để xem nó đang chạy ảnh số mấy
                # print(f"Frame: {self.anim_frame_idx} (State: {self.current_state})")

                # Nếu chạy vượt quá ảnh 24 -> Quay lại ảnh 9
                if self.anim_frame_idx > LOOP_END:
                    self.anim_frame_idx = LOOP_START
            
            # Các trạng thái khác (Waving...) -> Chạy thẳng
            else:
                self.anim_frame_idx += 1

            # Tiếp tục chạy
            self.anim_job = self.after(delay, lambda: self._animate_loop(frames, delay, play_once))
        
        else:
            # 3. Khi chạy hết danh sách ảnh (Chỉ xảy ra với Waving)
            if play_once:
                self.set_avatar_state("normal")
            else:
                # Phòng hờ: Nếu lỡ lọt vào đây thì reset về 0
                self.anim_frame_idx = 0
                self.anim_job = self.after(delay, lambda: self._animate_loop(frames, delay, play_once))

    # --- LOGIC CHAT ---
    def add_chat_bubble(self, role, text, is_loading=False):
        # (Logic vẽ bong bóng chat giữ nguyên từ code cũ)
        # Chỉ copy phần logic vẽ khung, label
        # ... [BẠN COPY LẠI HÀM add_chat_bubble TỪ FILE kiosk_ui.py CŨ VÀO ĐÂY] ...
        # Để ngắn gọn tôi viết tóm tắt:
        if role == "ai":
            container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            container.pack(anchor="w", padx=10, pady=5, fill="x")
            if is_loading: self.current_ai_container = container
            
            # Professional: White bubble with soft text
            bubble = ctk.CTkFrame(container, fg_color=AI_BUBBLE_COLOR, corner_radius=20)
            bubble.pack(side="left")
            label = ctk.CTkLabel(
                bubble, 
                text=text, 
                font=(FONT_FAMILY, 16), 
                text_color=TEXT_COLOR_DARK, 
                justify="left", 
                wraplength=self._bubble_wrap_length()
            )
            label.pack(padx=20, pady=15)
            try:
                self.message_labels.append(label)
            except Exception:
                pass
            
            if not is_loading: 
                self._add_speaker_btn(container, text)
                self._check_qr(container, text)
        else:
            container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            container.pack(anchor="e", padx=10, pady=5, fill="x")
            
            # Professional: Dark bubble with white text
            bubble = ctk.CTkFrame(container, fg_color=USER_BUBBLE_COLOR, corner_radius=20)
            bubble.pack(anchor="e", padx=10, pady=5)
            label = ctk.CTkLabel(
                bubble, 
                text=text, 
                font=(FONT_FAMILY, 16), 
                text_color=USER_TEXT_COLOR, 
                justify="right", 
                wraplength=self._bubble_wrap_length()
            )
            label.pack(padx=20, pady=15)
            try:
                self.message_labels.append(label)
            except Exception:
                pass

        self.after(50, self.scroll_bottom)
        return label

    def _add_speaker_btn(self, container, text):
        btn = ctk.CTkButton(container, image=assets.icons["speaker"], text="", width=30, height=30, 
                            fg_color="transparent", hover_color=BORDER_COLOR)
        
        # Bind click event with current button and text
        btn.configure(command=lambda b=btn, t=text: self._on_speaker_click(b, t))
        
        btn.pack(side="left", padx=10, anchor="s")
        return btn  # Return button reference

    def _clear_tts_queue(self):
        self.stop_requested = True
        with self.tts_queue.mutex:
            self.tts_queue.queue.clear()

    def _on_speaker_click(self, btn, text):
        # Case 1: Clicked the button that is currently playing -> STOP
        if self.current_playing_btn == btn:
            self._clear_tts_queue() # Ensure queue is cleared
            self.audio_client.stop()
            self._reset_speaker_btn(btn)
            self.current_playing_btn = None
            self._play_finish_animation()
            
        # Case 2: Clicked a new button (or nothing was playing) -> START
        else:
            # Stop any existing playback first
            if self.current_playing_btn:
                self._clear_tts_queue() # Ensure queue is cleared
                self.audio_client.stop()
                self._reset_speaker_btn(self.current_playing_btn)
            
            # Stop streaming if any
            self._clear_tts_queue()
            self.audio_client.stop()
            self.stop_requested = False # Reset for new playback

            # Set new state
            self.current_playing_btn = btn
            self.current_playing_text = text
            btn.configure(image=assets.icons["stop"]) # Change icon to STOP
            self.set_avatar_state("answering", play_once=False)
            
            # Define callback for when audio finishes naturally
            def on_finish():
                # Ensure we only reset if this button is still the active one
                if self.current_playing_btn == btn:
                    self.after(0, lambda: self._reset_speaker_btn(btn))
                    self.after(0, self._play_finish_animation)
                    self.current_playing_btn = None
                    self.current_playing_text = None

            # Play audio
            cleaned = self._clean_for_tts(text)
            if cleaned:
                self.audio_client.speak(cleaned, voice_name=TTS_VOICE_NAME, speed=TTS_SPEAKING_RATE, on_finish=on_finish)
            else:
                on_finish() # If nothing to play, finish immediately

    def _reset_speaker_btn(self, btn):
        try:
            btn.configure(image=assets.icons["speaker"])
        except: pass

    def _check_qr(self, container, text):
        if any(kw in text for kw in QR_KEYWORDS):
             self._append_qr(container, text)

    def _append_qr(self, container, text):
        try:
            bubble = container.winfo_children()[0]
            ctk.CTkFrame(bubble, height=1, fg_color=BORDER_COLOR).pack(fill="x", padx=20, pady=5)
            
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data("KẾT QUẢ TƯ VẤN:\n" + text)
            qr.make(fit=True)
            img = ctk.CTkImage(light_image=qr.make_image(fill_color="black", back_color="white").get_image(), size=(180, 180))
            
            ctk.CTkLabel(bubble, image=img, text="").pack(pady=10)
            self.scroll_bottom()
        except: pass

    def scroll_bottom(self):
        try:
            self.chat_frame.update_idletasks()
            self.chat_frame._parent_canvas.yview_moveto(1.0)
        except: pass

    def on_stop(self):
        """Called when user clicks the STOP button during generation"""
        self._clear_tts_queue()
        self.audio_client.stop()
        self.stop_requested = True
        self.set_generating_state(False)
        # Play closing animation instead of abrupt normal state
        self._play_finish_animation()

    def set_generating_state(self, is_generating):
        """
        is_generating=True: AI đang suy nghĩ/trả lời -> Nút Send thành Stop, Mic disable
        is_generating=False: Bình thường -> Nút Send xanh, Mic enable
        """
        if is_generating:
            # Send -> Stop (Red)
            self.btn_send.configure(
                image=assets.icons["stop"], 
                fg_color=DANGER, 
                hover_color="#991B1B",
                command=self.on_stop,
                state="normal"
            )
            # Mic disable
            self.btn_mic.configure(state="disabled")
            # Entry disable
            self.entry.configure(state="disabled")
        else:
            # Send -> Send (Green)
            self.btn_send.configure(
                image=assets.icons["send"], 
                fg_color="#10B981", 
                hover_color="#059669",
                command=self.on_send,
                state="normal"
            )
            # Mic enable
            self.btn_mic.configure(state="normal")
            # Entry enable
            self.entry.configure(state="normal")

    def set_listening_state(self, is_listening):
        """
        is_listening=True: Mic đang thu -> Nút Mic đỏ (Stop), Send disable, Entry hiện 'Đang nghe...'
        is_listening=False: Xong -> Mic xanh, Send enable
        """
        if is_listening:
            # Mic -> Stop Recording (Red)
            self.btn_mic.configure(
                image=assets.icons["stop"],
                fg_color=DANGER,
                hover_color="#991B1B",
                command=self.on_mic
            )
            # Send disable
            self.btn_send.configure(state="disabled")
            # Entry visual cue
            self.entry.configure(placeholder_text="🔴 Đang nghe... Nhấn lại để dừng", state="disabled")
            # Border highlight
            self.input_bg.configure(border_color=DANGER, border_width=2)
        else:
            # Mic -> Mic (Blue)
            self.btn_mic.configure(
                image=assets.icons["mic"],
                fg_color=ACCENT,
                hover_color="#0284C7",
                command=self.on_mic
            )
            # Send enable
            self.btn_send.configure(state="normal")
            # Entry revert
            self.entry.configure(placeholder_text="Nhập câu hỏi của bạn...", state="normal")
            # Border revert
            self.input_bg.configure(border_color=PRIMARY, border_width=1)

    # --- LOGIC EVENTS ---
    def on_send(self, event=None):
        text = self.entry.get().strip()
        if not text: return
        self.entry.delete(0, "end")
        self.add_chat_bubble("user", text)
        self.controller.reset_timer()
        
        # Reset keyboard state
        if not self.caps_locked:
            self.vkbd_shift = True
            self.shift_oneshot = True
            self.apply_shift_style()
            self.update_key_labels()
        
        self.set_generating_state(True)
        self.set_avatar_state("thinking")
        threading.Thread(target=self._thread_ask_ai, args=(text,), daemon=True).start()

    def on_mic(self):
        # Toggle Logic: If already listening (checked via attribute or state), stop it.
        # But currently on_mic just starts a thread. We need a flag.
        if getattr(self, "is_recording", False):
            # User wants to stop recording manually
            # Since audio_client.listen is blocking, we can't easily stop it unless we use a non-blocking stream
            # or kill the thread (unsafe). 
            # For now, we just update UI and let the listen timeout/finish.
            # OR if we had a proper stream client.
            # Assuming legacy listen() blocks until silence. 
            # We can't force stop 'speech_recognition' easily without logic change.
            # So we'll just update UI to show "Stopping..."
            self.status_label.configure(text="Đang xử lý...")
            return

        self.controller.reset_timer()
        self.is_recording = True
        self.set_listening_state(True)
        self.status_label.configure(text="Đang nghe...")
        self.set_avatar_state("listening")
        threading.Thread(target=self._thread_listen, daemon=True).start()

    def _thread_listen(self):
        def cb(msg): self.after(0, lambda: self.status_label.configure(text=msg))
        # Note: listen() blocks until silence
        text = self.audio_client.listen(status_callback=cb)
        self.after(0, lambda: self._on_listen_done(text))

    def _on_listen_done(self, text):
        self.is_recording = False
        self.set_listening_state(False)
        
        if text:
            self.on_send_submit(text) 
        else:
            self.set_avatar_state("normal")
            self.status_label.configure(text="Không nghe rõ.")

    def on_send_submit(self, text):
        self.add_chat_bubble("user", text)
        self.set_generating_state(True)
        self.set_avatar_state("thinking")
        threading.Thread(target=self._thread_ask_ai, args=(text,), daemon=True).start()

    def _thread_ask_ai(self, question):
        self.stop_requested = False
        self.after(0, lambda: setattr(self, "ai_bubble_label", self.add_chat_bubble("ai", "...", True)))
        
        # --- Start TTS Worker ---
        self.stop_tts = False
        while not self.tts_queue.empty():
            try: self.tts_queue.get_nowait()
            except: pass
        threading.Thread(target=self._process_tts_queue, daemon=True).start()
        
        full = ""
        # Removed buffer splitting logic to support full-text reading
        
        try:
            with requests.post(API_URL, json={"question": question, "history": [], "session_id": self.session_id}, stream=True, timeout=60) as res:
                first = True
                for chunk in res.iter_content(chunk_size=None, decode_unicode=True):
                    if self.stop_requested: break
                    clean = chunk.replace("__END__", "")
                    self.after(0, lambda c=clean, f=first: self._update_stream(c, f))
                    full += clean
                    first = False
                    
        except Exception as e:
            full += f"[Error: {e}]"
        finally:
            self.stop_tts = True 
            self.after(0, lambda: self._finalize_response(full))

    def _clean_for_tts(self, text):
        """Remove special characters from entire string for smoother TTS"""
        if not text: return ""
        # Remove markdown chars (*, #, _, `, ~) but keep standard punctuation
        # Also remove square brackets [] often used for links/citations
        cleaned = re.sub(r"[\*\#_`~\[\]]", "", text)
        return cleaned.strip()

    def _process_tts_queue(self):
        # Removed premature state change
        
        while not self.stop_requested:
            try:
                # Wait for text with timeout to check stop_requested
                text = self.tts_queue.get(timeout=0.5)
                
                # Check if this is a "Replay" action (full text) or stream
                # For stream, we just speak blocking
                if text:
                    self.after(0, lambda: self.set_avatar_state("answering", play_once=False))
                    self.audio_client.speak_blocking(text, voice_name=TTS_VOICE_NAME, speed=TTS_SPEAKING_RATE)
                    
                self.tts_queue.task_done()
            except queue.Empty:
                if self.stop_tts and self.tts_queue.empty():
                    break
            except Exception as e:
                print(f"TTS Worker Error: {e}")
                
        # When done (or stopped), play finish animation and reset button
        self.after(0, self._on_tts_finished)

    def _on_tts_finished(self):
        self._play_finish_animation()
        if self.current_playing_btn:
            self._reset_speaker_btn(self.current_playing_btn)
            self.current_playing_btn = None
            self.current_playing_text = None

    def _play_finish_animation(self):
        """
        Interrupt current animation and play the closing sequence (speak_024 -> speak_033).
        Then return to normal state.
        """
        # 1. Stop any running loop animation
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None
            
        self.current_state = "finishing"

        # 2. Get frames (RESIZED)
        frames = self._get_resized_frames("answering")
        if not frames:
            self.set_avatar_state("normal")
            return
            
        # 3. Slice frames: speak_024 (index 23) to speak_033 (index 32)
        # We take up to index 33 (exclusive) to include 32.
        # If the list is shorter, python slicing handles it safely.
        finish_frames = frames[23:33]
        
        if not finish_frames:
            self.set_avatar_state("normal")
            return

        self._animate_oneshot(finish_frames)

    def _animate_oneshot(self, frames, idx=0):
        if idx >= len(frames):
            self.set_avatar_state("normal")
            return
            
        self.avatar_label.configure(image=frames[idx])
        # Use self.anim_job so it can be cancelled if needed
        self.anim_job = self.after(60, lambda: self._animate_oneshot(frames, idx+1))

    def _update_stream(self, text, is_first):
        if self.ai_bubble_label:
            cur = self.ai_bubble_label.cget("text")
            new = text if is_first else (cur + text)
            self.ai_bubble_label.configure(text=new.replace("**",""))
            self.scroll_bottom()

    def _finalize_response(self, text):
        # If user stopped generation, don't queue TTS and don't set active state
        if self.stop_requested:
            if self.current_ai_container:
                self._add_speaker_btn(self.current_ai_container, text)
                self._check_qr(self.current_ai_container, text)
            return

        self.set_generating_state(False)
        # Queue full text for smooth reading
        if text and not text.startswith("[Error"):
            cleaned = self._clean_for_tts(text)
            if cleaned:
                self.tts_queue.put(cleaned)
        
        # Thêm nút loa và QR
        speaker_btn = None
        if self.current_ai_container:
            # Capture the button returned by _add_speaker_btn
            speaker_btn = self._add_speaker_btn(self.current_ai_container, text)
            self._check_qr(self.current_ai_container, text)

        # Update button state to "Playing" (Stop icon) because we just queued the text
        if speaker_btn and text and not text.startswith("[Error"):
             self.current_playing_btn = speaker_btn
             self.current_playing_text = text
             speaker_btn.configure(image=assets.icons["stop"])

    
