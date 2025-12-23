# frontend/screens/welcome.py
import customtkinter as ctk
from frontend.config import *
from frontend.assets import assets

class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, on_start_callback):
        super().__init__(parent, fg_color=BG_COLOR_WELCOME)
        self.on_start = on_start_callback
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        # Center Container
        container = ctk.CTkFrame(
            self, 
            fg_color="transparent"
        )
        container.place(relx=0.5, rely=0.5, anchor="center")

        # 1. Avatar (Compact for 600px height)
        avatar_img = assets.avatars.get("normal")
        if avatar_img:
            # Resize for welcome screen (Scale 50% from 500x550 -> 250x275)
            # Access internal PIL image to create new CTkImage with different size
            try:
                pil_img = avatar_img._light_image
                resized_avatar = ctk.CTkImage(light_image=pil_img, size=(250, 275))
                ctk.CTkLabel(container, text="", image=resized_avatar).pack(pady=(0, 10))
            except:
                # Fallback if internal access fails
                ctk.CTkLabel(container, text="", image=avatar_img).pack(pady=(0, 20))

        # 2. Title
        ctk.CTkLabel(
            container, 
            text="AI BANKING KIOSK", 
            font=(FONT_FAMILY, 32, "bold"), 
            text_color=PRIMARY
        ).pack(pady=(0, 5))

        # 3. Subtitle
        ctk.CTkLabel(
            container, 
            text="Trợ lý ảo thông minh - Hỗ trợ 24/7", 
            font=(FONT_FAMILY, 16), 
            text_color=TEXT_COLOR_LIGHT
        ).pack(pady=(0, 20))

        # 4. Start Button (Compact Hero Button)
        btn_start = ctk.CTkButton(
            container, 
            text="BẮT ĐẦU TƯ VẤN", 
            command=self.on_start,
            font=(FONT_FAMILY, 16, "bold"), 
            height=50, 
            width=240, 
            corner_radius=25,
            fg_color=PRIMARY, 
            hover_color=PRIMARY_HOVER,
        )
        btn_start.pack(pady=10)

        # 5. Footer / Version
        #ctk.CTkLabel(
        #    self, 
        #    text="Powered by Banking RAG Agent v2.0", 
        #    font=(FONT_FAMILY, 12), 
        #    text_color=MUTED
        #).place(relx=0.5, rely=0.95, anchor="center")
