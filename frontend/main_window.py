# frontend/main_window.py
import customtkinter as ctk
from frontend.config import *
from frontend.screens.welcome import WelcomeScreen
from frontend.screens.chat import ChatScreen

class KioskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(1024, 600)
        self.resizable(True, True)
        
        self.current_frame = None
        self.idle_timer = None
        
        self.show_welcome()

    def show_welcome(self):
        self._clear_frame()
        self.current_frame = WelcomeScreen(self, on_start_callback=self.show_chat)
        self.current_frame.pack(fill="both", expand=True)
        self._stop_timer() # Welcome screen không cần timer

    def show_chat(self):
        self._clear_frame()
        self.current_frame = ChatScreen(self, controller=self)
        self.current_frame.pack(fill="both", expand=True)
        self.reset_timer()

    def _clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

    def reset_timer(self, event=None):
        self._stop_timer()
        # Sau 5 phút không làm gì -> Về màn hình chào
        self.idle_timer = self.after(IDLE_TIMEOUT, self.show_welcome)

    def _stop_timer(self):
        if self.idle_timer:
            self.after_cancel(self.idle_timer)
            self.idle_timer = None

    # --- Window control helpers (removed for previous interface state) ---
