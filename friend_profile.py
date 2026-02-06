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
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

import json
import requests


# Supabase =============================================================================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def get_user_by_mail(user_mail: str):
    """user_mail から Supabase users テーブルを検索"""
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {"user_mail": f"eq.{user_mail}", "select": "*"}
    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        print("Supabase Error:", r.text)
        return None

    data = r.json()
    return data[0] if data else None


# UI scaling ============================================================================
LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236/255, 244/255, 232/255, 1)

scale = Window.dpi / 120.0

def Sdp(v):
    return dp(v * scale)

def Ssp(v):
    return sp(v * scale)


# UI Parts ==============================================================================
class ImageCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = Sdp(10)
        self.size_hint = (None, None)
        self.size = (Sdp(160), Sdp(160))
        with self.canvas.before:
            Color(0.67, 0.91, 0.51, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(25)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


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
            size_hint=(None, None),
            allow_stretch=True,
            keep_ratio=False,
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


class RoundedButton(Button):
    def __init__(self, **kwargs):
        bg = kwargs.pop("background_color", (0.671, 0.906, 0.510, 1))
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(*bg)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(25)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# Profile Screen ==========================================================================
class FriendProfileScreen(Screen):
    def __init__(self, friend_mail=None, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        
        # 背景色を設定（重要：2回目以降の背景色問題を修正）
        with self.canvas.before:
            Color(236/255, 244/255, 232/255, 1)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        self.friend_mail = friend_mail
        self.app_instance = app_instance

        user = get_user_by_mail(friend_mail)
        if user:
            user_name = user["user_name"]
            img_url = user["icon_url"]
        else:
            user_name = "不明なユーザー"
            img_url = "img/default_user.png"

        root_layout = BoxLayout(
            orientation="vertical",
            spacing=Sdp(30),
            size_hint=(None, None),
            size=(Sdp(420), Sdp(300))
        )

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(root_layout)

        profile_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(20),
            size_hint_y=None,
            height=Sdp(180)
        )
        profile_layout.add_widget(Widget(size_hint_x=0.1))

        img_card = ImageCard()
        circle = CircleImageView(
            source=img_url,
            size_hint=(None, None),
            size=(Sdp(140), Sdp(140))
        )
        img_card.add_widget(circle)
        profile_layout.add_widget(img_card)

        name_layout = BoxLayout(orientation="vertical")
        name_label = Label(
            text=user_name,
            font_name="Japanese",
            font_size=Ssp(28),
            color=(0, 0, 0, 1),
            size_hint=(1, None),
            height=Sdp(140)
        )
        name_layout.add_widget(name_label)
        profile_layout.add_widget(name_layout)

        root_layout.add_widget(profile_layout)

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
        meet_button = RoundedButton(
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
        row1.add_widget(meet_button)
        root_layout.add_widget(row1)

        row2 = AnchorLayout(
            anchor_x="left",
            anchor_y="center",
            size_hint_y=None,
            height=Sdp(90)
        )
        del_button = RoundedButton(
            text="削除",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.60, 0.80, 0.90, 1),
            on_press=self.on_delete_press
        )
        row2.add_widget(del_button)
        root_layout.add_widget(row2)

        self.add_widget(anchor)
    
    def _update_bg(self, *args):
        """背景矩形を更新"""
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos
    
    def on_enter(self):
        """画面遷移時に背景色を設定（2回目以降の背景色問題を修正）"""
        Window.clearcolor = (236/255, 244/255, 232/255, 1)

    def on_chat_press(self, instance):
        print("チャットを開始（相手メール →", self.friend_mail, ")")
        if self.app_instance:
            self.app_instance.open_chat("MY_MAIL", self.friend_mail)

    def on_meeting_press(self, instance):
        print("待ち合わせ開始：", self.friend_mail)
        if not self.app_instance:
            print("⚠️ app_instance が見つかりません")
            return
        if hasattr(self.app_instance, 'open_meeting_map'):
            self.app_instance.open_meeting_map(self.friend_mail)
        else:
            print("⚠️ open_meeting_map メソッドが見つかりません")

    def on_delete_press(self, instance):
        print("友達削除：", self.friend_mail)
        instance.disabled = True
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                my_mail = data[0].get("user_mail")
            else:
                my_mail = data.get("user_mail")

            if not my_mail or not self.friend_mail:
                print("⚠️ user_mail が取得できません")
                instance.disabled = False
                return

            url = f"{SUPABASE_URL}/rest/v1/friend"
            params = {
                "or": (
                    f"(and(send_user.eq.{my_mail},recive_user.eq.{self.friend_mail}),"
                    f"and(send_user.eq.{self.friend_mail},recive_user.eq.{my_mail}))"
                )
            }
            data = {"permission": False}
            headers_patch = headers.copy()
            headers_patch["Content-Type"] = "application/json"

            res = requests.patch(url, headers=headers_patch, params=params, json=data, timeout=10)
            print(f"📡 削除応答: status={res.status_code}")
            if res.status_code in (200, 204):
                print("✅ 友達削除成功（permission=false）")
                if self.app_instance and hasattr(self.app_instance, "back_to_map"):
                    self.app_instance.back_to_map()
            else:
                print(f"❌ 友達削除失敗: {res.status_code} {res.text}")
                instance.disabled = False
        except Exception as e:
            print(f"❌ 友達削除エラー: {e}")
            instance.disabled = False


if __name__ == "__main__":
    App().run()