import threading
import time
from app import app
from kivy.app import App
from kivy.uix.label import Label

class StrollerApp(App):
    def build(self):
        # Jalankan server Flask di background
        threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False), daemon=True).start()
        time.sleep(1) # Beri waktu server untuk menyala
        return Label(text="Server berjalan...") # (Nanti kita ganti dengan WebView)

if __name__ == '__main__':
    StrollerApp().run()
