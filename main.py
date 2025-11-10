from kivy.app import App
from kivy.uix.label import Label

class MyApp(App):
    def build(self):
        return Label(
            text="こんにちは、世界！",
            font_name="NotoSansJP-Regular.ttf",  # フォントファイル名
            font_size=32
        )

if __name__ == "__main__":
    MyApp().run()