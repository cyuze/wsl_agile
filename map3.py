# -*- coding: utf-8 -*-
from kivy.app import App
from kivy_garden.mapview import MapView, MapMarker, MapSource
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image, AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.uix.stencilview import StencilView
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.text import LabelBase

from map3_service import (
    MainScreenLogic,
    request_location_permissions,
    get_active_meeting_info
)

LabelBase.register(name='NotoSansJP', fn_regular='NotoSansJP-Regular.ttf')


# ========================
# Map Source
# ========================
class GSImapSource(MapSource):
    def __init__(self, **kwargs):
        super().__init__(
            url="https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
            attribution="地理院地図",
            tile_size=256,
            image_ext="png",
            max_zoom=18,
            min_zoom=5,
            **kwargs
        )


# ========================
# UI パーツ
# ========================
class ImageButton(ButtonBehavior, FloatLayout):
    def __init__(self, image_source, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.671, 0.905, 0.510, 1)
            self.bg = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.icon = Image(
            source=image_source,
            size_hint=(None, None),
            size=(50, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.icon)

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos


class FriendIconButton(ButtonBehavior, FloatLayout):
    def __init__(self, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.size = (100, 100)
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(size=self.size, pos=self.pos)
            StencilUse()

        self.image = AsyncImage(source=icon_url, allow_stretch=True, keep_ratio=False, size=self.size)
        self.add_widget(self.image)

        with self.canvas.after:
            StencilUnUse()
            StencilPop()

        self.bind(pos=self.update_mask, size=self.update_mask)

    def update_mask(self, *args):
        self.mask.pos = self.pos
        self.mask.size = self.size
        self.image.pos = self.pos
        self.image.size = self.size

    def on_press(self):
        if self.app_instance:
            self.app_instance.open_friend_profile(self.friend_mail)


class FriendMarker(MapMarker):
    def __init__(self, lat, lon, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        self.container = FriendIconButton(icon_url, friend_mail, app_instance)
        self.add_widget(self.container)
        self.bind(pos=self.update_container)

    def update_container(self, *args):
        self.container.pos = self.pos


# ========================
# Main Screen
# ========================
class MainScreen(FloatLayout):
    def __init__(self, app_instance=None, friend_mail=None, place_name=None, meeting_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.friend_mail = friend_mail
        self.place_name = place_name
        self.meeting_id = meeting_id  

        print(f"🔍 DEBUG: map3.MainScreen initialized with meeting_id = {self.meeting_id}")

        Window.clearcolor = (1, 1, 1, 1)

        # ... (以下のコードは変更なし)

        # -------------------------
        # MapView
        # -------------------------
        self.mapview = MapView(
            lat=35.6762,
            lon=139.6503,
            zoom=14,
            map_source=GSImapSource()
        )
        self.add_widget(self.mapview)

        # -------------------------
        # 上部バー
        # -------------------------
        self.meeting_bar = FloatLayout(size_hint=(1, None), height=90, pos_hint={'top': 1})

        with self.meeting_bar.canvas.before:
            Color(1, 1, 1, 0.9)
            self.meeting_bg = RoundedRectangle(size=self.meeting_bar.size, pos=self.meeting_bar.pos, radius=[20])
        self.meeting_bar.bind(size=self._update_meeting_bg, pos=self._update_meeting_bg)

        self.meeting_status_label = Label(
            text="待ち合わせ中",
            size_hint=(None, None),
            size=(300, 40),
            pos_hint={'x': 0.03, 'center_y': 0.7},
            color=(0, 0, 0, 1),
            font_size=22,
            font_name="NotoSansJP"
        )

        self.meeting_friend_label = Label(
            text="相手: 読み込み中…",
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'x': 0.03, 'center_y': 0.4},
            color=(0.2, 0.2, 0.2, 1),
            font_size=18,
            font_name="NotoSansJP"
        )

        self.meeting_place_label = Label(
            text="場所: 読み込み中…",
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'x': 0.03, 'center_y': 0.15},
            color=(0.2, 0.2, 0.2, 1),
            font_size=18,
            font_name="NotoSansJP"
        )

        self.end_button = Button(
            text="終了",
            size_hint=(None, None),
            size=(140, 60),
            pos_hint={'right': 0.97, 'center_y': 0.5},
            background_normal="",
            background_color=(0.671, 0.905, 0.510, 1),
            color=(0, 0, 0, 1),
            font_size=20,
            font_name="NotoSansJP"
        )

        self.meeting_bar.add_widget(self.meeting_status_label)
        self.meeting_bar.add_widget(self.meeting_friend_label)
        self.meeting_bar.add_widget(self.meeting_place_label)
        self.meeting_bar.add_widget(self.end_button)
        self.add_widget(self.meeting_bar)

        # -------------------------
        # 下部ボタン
        # -------------------------
        btn_friend = ImageButton(image_source='img/friend.png',
                                 size_hint=(None, None), size=(140, 140),
                                 pos_hint={'center_x': 0.2, 'y': 0.05})

        btn_chat = ImageButton(image_source='img/chat.png',
                               size_hint=(None, None), size=(140, 140),
                               pos_hint={'center_x': 0.5, 'y': 0.05})

        btn_settings = ImageButton(image_source='img/settings.png',
                                   size_hint=(None, None), size=(140, 140),
                                   pos_hint={'center_x': 0.8, 'y': 0.05})

        self.add_widget(btn_friend)
        self.add_widget(btn_chat)
        self.add_widget(btn_settings)

        # -------------------------
        # ロジック
        # -------------------------
        self.logic = MainScreenLogic(self)

        self.end_button.bind(on_press=self.logic.on_end_meeting)
        btn_friend.bind(on_press=self.logic.on_friend_button)
        btn_chat.bind(on_press=self.logic.on_chat_button)
        btn_settings.bind(on_press=self.logic.on_settings_button)

        # -------------------------
        # Supabase から meeting 情報を読み込み
        # -------------------------
        Clock.schedule_once(lambda dt: self.load_meeting_info(), 0.5)

    # -------------------------
    # meeting 情報読み込み
    # -------------------------
    def load_meeting_info(self):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = f.read()
            user = json.loads(data)[0]
            my_mail = user.get("user_mail")

            info = get_active_meeting_info(my_mail)
            if info:
                lat, lon = info["location"]
                place_name = info["place_name"]
                members = info["members"]
                self.meeting_id = info["meeting_id"]  # meeting_id を更新

                self.mapview.center_on(lat, lon)
                self.meeting_place_label.text = f"場所: {place_name}"

                others = [m for m in members if m != my_mail]
                self.meeting_friend_label.text = f"相手: {', '.join(others)}"

        except Exception as e:
            print(f"⚠️ load_meeting_info error: {e}")

    # -------------------------
    # 上部バー背景更新
    # -------------------------
    def _update_meeting_bg(self, *args):
        self.meeting_bg.size = self.meeting_bar.size
        self.meeting_bg.pos = self.meeting_bar.pos


# ========================
# App
# ========================
class MyApp(App):
    def __init__(self, friend_mail=None, place_name=None, **kwargs):
        super().__init__(**kwargs)
        self.friend_mail = friend_mail
        self.place_name = place_name

    def build(self, meeting_id):
        request_location_permissions()
        self.main_screen = MainScreen(app_instance=self, friend_mail=self.friend_mail, place_name=self.place_name, meeting_id=meeting_id)
        return self.main_screen
    

    def back_to_map(self):
        self.root.clear_widgets()
        self.main_screen = MainScreen(app_instance=self)
        self.root.add_widget(self.main_screen)

    def open_settings(self):
        self.root.clear_widgets()
        from settings import SettingsScreen
        self.root.add_widget(SettingsScreen(app_instance=self))

    def open_friend_addition(self):
        self.root.clear_widgets()
        from addition import FriendApp
        self.root.add_widget(FriendApp())

    def open_friend_profile(self, friend_mail):
        self.root.clear_widgets()
        from friend_profile import FriendProfileScreen
        self.root.add_widget(FriendProfileScreen(friend_mail, app_instance=self))

    def open_chat_list(self):
        self.root.clear_widgets()
        from chat_screen import MainLayout
        self.root.add_widget(MainLayout(app_instance=self))
        



if __name__ == '__main__':
    MyApp().run()