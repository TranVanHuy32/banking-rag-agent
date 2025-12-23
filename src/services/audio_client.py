import requests
import speech_recognition as sr
import pygame
import tempfile
import os
import time
import threading

class AudioClient:
    def __init__(self, tts_url):
        self.tts_url = tts_url
        try:
            pygame.mixer.init()
        except:
            print("Warning: Pygame mixer init failed")

    def speak_blocking(self, text, voice_name="vi-VN-Standard-A", speed=1.0):
        """
        Phiên bản blocking của hàm speak, dùng cho queue worker.
        """
        tmp_path = None
        try:
            payload = {
                "text": text[:2000],  # Increased limit for smoother full-text reading
                "voice_name": voice_name,
                "speaking_rate": speed,
                "audio_encoding": "MP3"
            }
            # Gọi API TTS
            response = requests.post(self.tts_url, json=payload, timeout=20) # Increased timeout
            
            if response.ok:
                # Lưu file tạm
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                    fp.write(response.content)
                    tmp_path = fp.name
                
                # Phát âm thanh
                if pygame.mixer.get_init():
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    
                    # Chờ phát xong
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                        
            else:
                print(f"TTS Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"TTS Exception: {e}")
        finally:
            # Dọn dẹp file tạm
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

    def speak(self, text, voice_name="vi-VN-Standard-A", speed=1.0, on_finish=None):
        """
        Gửi text tới server TTS, nhận về file audio (bytes) và phát bằng pygame.
        """
        def _run():
            self.speak_blocking(text, voice_name, speed)
            if on_finish:
                on_finish()

        # Chạy trong luồng riêng để không chặn UI
        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        """Dừng phát âm thanh ngay lập tức."""
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except:
            pass

    def listen(self, status_callback=None):
        """
        Thu âm từ microphone và chuyển thành văn bản (STT).
        Sử dụng thư viện speech_recognition (Google Speech API).
        Hàm này BLOCKING (nên gọi trong thread).
        """
        r = sr.Recognizer()
        with sr.Microphone() as source:
            # Tự động chỉnh độ nhạy mic
            r.adjust_for_ambient_noise(source, duration=0.5)
            
            if status_callback:
                status_callback("Đang nghe...")
            
            try:
                # Lắng nghe (tối đa 5s chờ, 10s thu)
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                
                if status_callback:
                    status_callback("Đang xử lý...")
                
                # Gọi Google STT (cần mạng)
                text = r.recognize_google(audio, language="vi-VN")
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except Exception as e:
                print(f"STT Error: {e}")
                return None
