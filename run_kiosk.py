# run_kiosk.py
import customtkinter as ctk
from frontend.main_window import KioskApp
import os
import platform

# Fix lỗi hiển thị trên màn hình cảm ứng Pi (tùy chọn)
if os.environ.get('DISPLAY','') == '':
    print('No display found. Using :0.0')
    os.environ.__setitem__('DISPLAY', ':0.0')

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = KioskApp()
    
    # Maximized (not fullscreen)
    try:
        # Windows
        app.state('zoomed')
    except Exception:
        # Fallback: set to screen size
        sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
        app.geometry(f"{sw}x{sh}+0+0")
    
    # Optional: Bind Escape to restore normal state for debugging
    app.bind("<Escape>", lambda event: app.state('normal'))
    
    app.mainloop()
