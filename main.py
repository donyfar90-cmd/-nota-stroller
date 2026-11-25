import threading
from kivy.app import App
from kivy.uix.label import Label
from app import app, init_db


def start_flask():
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


class NotaStrollerApp(App):
    def build(self):
        return Label(
            text="Server Nota Stroller aktif di:\nhttp://127.0.0.1:5000\n\nBuka alamat tersebut di browser HP.",
            halign="center",
        )


if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    NotaStrollerApp().run()
