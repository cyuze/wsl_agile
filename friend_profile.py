from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.switch import Switch
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen, ScreenManager

import os
import requests

SUPABASE_URL = 'https://impklpvfmyvydnoayhfj.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4'

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def get_user_by_name(user_name: str):
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {"user_name": f"eq.{user_name}", "select": "*"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Supabase Error: {res.status_code} → {res.text}")
    data = res.json()
    if not data:
        return None
    return data[0]

row = get_user_by_name("reirei")
if row is None:
    raise Exception("ユーザーが見つかりませんでした。")

user_name = row["user_name"]
img_url = row["icon_url"]

LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236 / 255, 244 / 255, 232 / 255, 1)

# === スケーリング係数 ===
scale = Window.dpi / 120.0   # 160dpiを基準に拡大

def Sdp(value):  # Scaled dp
    return dp(value * scale)

def Ssp(value):  # Scaled sp
    return sp(value * scale)

# 画像カード
class ImageCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = Sdp(10)
        self.size_hint = (None, None)
        self.size = (Sdp(160), Sdp(160))  # ←大きめに
        with self.canvas.before:
            self.rect = RoundedRectangle(
                background_color = Color(0.67, 0.91, 0.51, 1),
                pos=self.pos,
                size=self.size,
                radius=[Sdp(25)]
            )
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# 丸アイコン
class CircleImageView(StencilView):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        self.img = AsyncImage(
            source=self.source,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(None, None),
            size=self.size
        )
        self.add_widget(self.img)
        with self.canvas.after:
            StencilUnUse()
            StencilPop()
        self.bind(pos=self.update_mask, size=self.update_mask)

    def update_mask(self, *args):
        self.mask.pos = self.pos
        self.mask.size = self.size
        self.img.pos = self.pos
        self.img.size = self.size

# 角丸ボタン
class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        bg_color = kwargs.pop("background_color", (0.671, 0.906, 0.510, 1))
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            self.bg_color_instruction = Color(rgba=bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(25)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# プロフィール画面
class FriendProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ルートレイアウト
        root_layout = BoxLayout(
            orientation="vertical",
            spacing=Sdp(30),
            size_hint=(None, None),
            size=(Sdp(420), Sdp(300))
        )

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(root_layout)


        # プロフィール部分
        profile_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(20),
            size_hint_y=None,
            height=Sdp(180)
        )
        profile_layout.add_widget(Widget(size_hint_x=0.1))

        image_card = ImageCard()
        profile_icon = CircleImageView(
            source=img_url,
            size_hint=(None, None),
            size=(Sdp(140), Sdp(140))
        )
        image_card.add_widget(profile_icon)
        profile_layout.add_widget(image_card)

        profile_name_layout = BoxLayout(orientation="vertical")
        profile_name = Label(
            text=user_name,
            font_name="Japanese",
            font_size=Ssp(28),
            color=(0, 0, 0, 1),
            size_hint=(1, None),
            height=Sdp(140)
        )
        profile_name_layout.add_widget(profile_name)
        profile_layout.add_widget(profile_name_layout)

        root_layout.add_widget(profile_layout)

        # ボタン行1
        row1 = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(60),
            size_hint_y=None,
            height=Sdp(80)
        )
        chat_button = RoundedButton(
            text="チャット",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.67, 0.90, 0.51, 1),
            on_press=self.on_chat_press
        )
        meeting_button = RoundedButton(
            text="待ち合わせする",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.67, 0.90, 0.51, 1),
            on_press=self.on_meeting_press
        )
        row1.add_widget(chat_button)
        row1.add_widget(meeting_button)
        root_layout.add_widget(row1)

        # ボタン行2（削除）
        row2 = AnchorLayout(
            anchor_x="left",
            anchor_y="center",
            size_hint_y=None,
            height=Sdp(90)
        )
        delete_button = RoundedButton(
            text="削除",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.60, 0.80, 0.90, 1),
            on_press=self.on_delete_press
        )
        row2.add_widget(delete_button)
        root_layout.add_widget(row2)

        # 最後に Screen に追加
        self.add_widget(anchor)


    # イベントハンドラ
    def on_chat_press(self, instance):
        print("チャットボタンが押されました。")

    def on_meeting_press(self, instance):
        print("待ち合わせボタンがクリックされました。")

    def on_delete_press(self, instance):
        print("お友達を手放しました。")
        
    def go_back(self, *args):
        self.manager.current = "settings"


class FriendProfileApp(App):
    def build(self):
        return FriendProfileScreen()

if __name__ == "__main__":
    FriendProfileApp().run()
