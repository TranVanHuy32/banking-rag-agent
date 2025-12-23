# frontend/assets.py
import customtkinter as ctk
from PIL import Image
import os
import sys
import re

class AssetsManager:
    def __init__(self):
        # --- SỬA LỖI ĐƯỜNG DẪN TẠI ĐÂY ---
        # 1. Lấy đường dẫn của file assets.py này (đang nằm trong folder frontend)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Lùi ra 1 cấp để về thư mục gốc (banking-rag-agent)
        project_root = os.path.dirname(current_file_dir)
        
        # 3. Trỏ vào thư mục assets
        self.base_path = os.path.join(project_root, "assets")
        self.avatar_path = os.path.join(self.base_path, "avatar")
        
        # [DEBUG] In ra để kiểm tra xem đường dẫn đúng chưa
        print(f"--- ASSETS DEBUG ---")
        print(f"Project Root: {project_root}")
        print(f"Looking for assets in: {self.base_path}")
        
        if not os.path.exists(self.base_path):
            print(f"❌ LỖI: Không tìm thấy thư mục assets!")
        else:
            print(f"✅ Đã tìm thấy thư mục assets.")

        self.icons = {}
        self.avatars = {}
        
        self._load_icons()
        self._load_avatars()

    def _load_icons(self):
        def load(name, size=(24, 24)): # Tăng size icon lên chút cho rõ
            p = os.path.join(self.base_path, name)
            if os.path.exists(p): 
                return ctk.CTkImage(Image.open(p), size=size)
            print(f"⚠️ Thiếu icon: {name} (tại {p})")
            return None

        # Đảm bảo tên file trong code khớp với tên file thực tế trong folder assets
        self.icons["send"] = load("send_icon.png")
        self.icons["mic"] = load("mic_icon.png")
        self.icons["stop"] = load("stop_icon.png", size=(20, 20))
        self.icons["speaker"] = load("speaker_icon.png", size=(24, 24))

    def _load_avatars(self):
        def load_ava(name, size=(300, 350)): # Kích thước ảnh nhân vật
            p = os.path.join(self.avatar_path, name)
            if os.path.exists(p): 
                return ctk.CTkImage(Image.open(p), size=size)
            print(f"⚠️ Thiếu avatar: {name} (tại {p})")
            return None
        
        # [MỚI] Hàm load cả thư mục thành 1 danh sách ảnh
        def load_folder_sequence(folder_name, size=(300, 350)):
            frames = []
            folder_path = os.path.join(self.avatar_path, folder_name)
            
            if not os.path.exists(folder_path):
                print(f"⚠️ Không tìm thấy folder anim: {folder_name}")
                return []

            # Lấy tất cả file png, sắp xếp theo tên (001, 002...)
            files = sorted([f for f in os.listdir(folder_path) if f.endswith('.png')])
            
            print(f"Loading {len(files)} frames from {folder_name}...")
            
            for f in files:
                img_path = os.path.join(folder_path, f)
                # Load ảnh
                frames.append(ctk.CTkImage(Image.open(img_path), size=size))
            
            return frames

        # Đảm bảo bạn đã copy ảnh vào banking-rag-agent/assets/avatar/
        self.avatars["normal"] = load_ava("normal.png")
        self.avatars["listening"] = load_ava("listening.png")
        self.avatars["thinking"] = load_ava("thinking.png")
        self.avatars["answering_anim"] = load_folder_sequence("answering")
        self.avatars["waving_anim"] = load_folder_sequence("waving")

# Singleton instance
assets = AssetsManager()
