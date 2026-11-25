from kivy.app import App
from kivy.uix.label import Label

class NotaStrollerApp(App):
    def build(self):
        return Label(text="Aplikasi Berhasil Dibuat!")

if __name__ == '__main__':
    NotaStrollerApp().run()
