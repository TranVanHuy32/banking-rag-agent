# frontend/config.py

# --- API ---
API_URL = "http://localhost:8000/api/v1/chat/query"
TTS_URL = "http://localhost:8000/api/v1/tts/speak"

# --- APP SETTINGS ---
APP_TITLE = "Bank Kiosk AI"
WINDOW_SIZE = "1024x600" # Tăng kích thước mặc định cho thoáng
IDLE_TIMEOUT = 300000  # 5 phút

# --- FONTS ---
# Ưu tiên Segoe UI (Windows) hoặc Roboto (Cross-platform)
FONT_FAMILY = "Segoe UI" 

# --- COLORS (PROFESSIONAL FINTECH THEME) ---
BG_COLOR_WELCOME = "#F8FAFC" # Slate 50
BG_COLOR_CHAT = "#F1F5F9"    # Slate 100
CARD_BG = "#FFFFFF"

# Borders & Separators
BORDER_COLOR = "#E2E8F0"     # Slate 200 - Nhẹ nhàng
BLACK_BORDER = "#CBD5E1"     # Slate 300 - Thay cho màu đen gắt

# Brand Colors (Trustworthy Blue)
PRIMARY = "#0F172A"          # Slate 900 (Deep Navy) - Sang trọng
PRIMARY_HOVER = "#1E293B"    # Slate 800
ACCENT = "#0EA5E9"           # Sky 500 - Điểm nhấn hiện đại
SUCCESS = "#10B981"          # Emerald 500
DANGER = "#EF4444"           # Red 500
MUTED = "#64748B"            # Slate 500

# Chat Bubbles
USER_BUBBLE_COLOR = "#0F172A" # Dark Bubble for User (High Contrast)
USER_TEXT_COLOR = "#FFFFFF"   # White text on Dark Bubble

AI_BUBBLE_COLOR = "#FFFFFF"   # White Bubble for AI
TEXT_COLOR_DARK = "#1E293B"   # Slate 800
TEXT_COLOR_LIGHT = "#475569"  # Slate 600

# Virtual Keyboard
KEYBOARD_BG = "#CBD5E1"       # Slate 300 (iOS Style BG)
KEY_BG = "#FFFFFF"            # White Keys
KEY_TEXT = "#0F172A"
CAPS_COLOR = "#0EA5E9"        # Active State

# --- TTS SETTINGS ---
TTS_VOICE_NAME = "vi-VN-Standard-A"
TTS_SPEAKING_RATE = 1.1

# --- KEYWORDS FOR QR ---
QR_KEYWORDS = ["BẢNG TÍNH", "DỰ TÍNH", "KẾ HOẠCH", "THÔNG TIN GÓI", "LÃI SUẤT", "TỶ GIÁ", "GIÁ VÀNG", "BẢNG GIÁ"]
