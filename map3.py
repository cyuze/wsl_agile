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
import random
import requests
import json
import threading

from map_service import (
    save_my_location, fetch_friends_by_mail,
    fetch_friend_icon, fetch_friend_location,
    initialize_user_location
)

from personal_chat_screen import ChatScreen

# ========================
# 日本語フォント登録
# ========================
LabelBase.register(name='NotoSansJP', fn_regular='NotoSansJP-Regular.ttf')

# Android 権限
try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False

def request_location_permissions():
    if ANDROID:
        request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION])
    else:
        print("⚠️ Android以外なので権限要求スキップ")

SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "YOUR_KEY"

MY_USER_MAIL = None

try:
    from plyer import gps
    HAS_GPS = True
except ImportError:
    HAS_GPS = False


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
        print("🧑 フレンドアイコン押された:", self.friend_mail)
        if self.app_instance:
            self.app_instance.open_friend_profile(self.friend_mail)


class FriendMarker(MapMarker):
    def __init__(self, lat, lon, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        self.container = FriendIconButton(
            icon_url=icon_url,
            friend_mail=friend_mail,
            app_instance=app_instance
        )
        self.add_widget(self.container)
        self.bind(pos=self.update_container)

    def update_container(self, *args):
        self.container.pos = self.pos


class MainScreen(FloatLayout):
    def __init__(self, app_instance=None, friend_mail=None, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.friend_mail = friend_mail
        Window.clearcolor = (1, 1, 1, 1)

        print(f"🔍 DEBUG: MainScreen initialized, friend_mail={self.friend_mail}")

        self.friend_markers = {}
        self.my_marker = None

        self.initialize_user_location_on_open()

        # ========================
        # MapView
        # ========================
        self.mapview = MapView(lat=35.6762, lon=139.6503, zoom=14, map_source=GSImapSource())
        self.add_widget(self.mapview)
        self.map_center_updated = False

        # ========================
        # 待ち合わせ上部バー
        # ========================
        self.meeting_bar = FloatLayout(
            size_hint=(1, None),
            height=90,
            pos_hint={'top': 1}
        )

        with self.meeting_bar.canvas.before:
            Color(1, 1, 1, 0.9)
            self.meeting_bg = RoundedRectangle(
                size=self.meeting_bar.size,
                pos=self.meeting_bar.pos,
                radius=[20]
            )
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

        friend_text = self.friend_mail if self.friend_mail else "（相手未選択）"
        self.meeting_friend_label = Label(
            text=f"相手: {friend_text}",
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'x': 0.03, 'center_y': 0.4},
            color=(0.2, 0.2, 0.2, 1),
            font_size=18,
            font_name="NotoSansJP"
        )

        self.meeting_place_label = Label(
            text="場所: 未設定",
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'x': 0.03, 'center_y': 0.15},
            color=(0.2, 0.2, 0.2, 1),
            font_size=18,
            font_name="NotoSansJP"
        )

        # 右上 終了ボタン（テキスト版・緑色）
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
        self.end_button.bind(on_press=self.on_end_meeting)

        self.meeting_bar.add_widget(self.meeting_status_label)
        self.meeting_bar.add_widget(self.meeting_friend_label)
        self.meeting_bar.add_widget(self.meeting_place_label)
        self.meeting_bar.add_widget(self.end_button)
        self.add_widget(self.meeting_bar)

        # ========================
        # 下部ボタン
        # ========================
        btn_friend = ImageButton(image_source='img/friend.png',
                                 size_hint=(None, None), size=(140, 140),
                                 pos_hint={'center_x': 0.2, 'y': 0.05})
        btn_friend.bind(on_press=self.on_friend_button)
        self.add_widget(btn_friend)

        btn_chat = ImageButton(
            image_source='img/chat.png',
            size_hint=(None, None), size=(140, 140),
            pos_hint={'center_x': 0.5, 'y': 0.05}
        )
        btn_chat.bind(on_press=self.on_chat_button)
        self.add_widget(btn_chat)

        btn_settings = ImageButton(image_source='img/settings.png',
                                   size_hint=(None, None), size=(140, 140),
                                   pos_hint={'center_x': 0.8, 'y': 0.05})
        btn_settings.bind(on_press=self.on_settings_button)
        self.add_widget(btn_settings)

        # ========================
        # GPS / デバッグ
        # ========================
        if HAS_GPS:
            try:
                gps.configure(on_location=self.on_location, on_status=self.on_status)
                gps.start()
                print("📡 GPSモードで起動")
            except:
                self.start_debug_mode()
        else:
            self.start_debug_mode()

        self.friend_update_event = Clock.schedule_interval(self.update_friends, 15)
        self.send_location_event = Clock.schedule_interval(self.send_my_location, 30)
        Clock.schedule_once(lambda dt: self.send_my_location(dt), 0.5)

        if not HAS_GPS:
            self.location_event = Clock.schedule_interval(self.simulate_location, 3)

    # ========================
    # 待ち合わせUI用
    # ========================
    def _update_meeting_bg(self, *args):
        self.meeting_bg.size = self.meeting_bar.size
        self.meeting_bg.pos = self.meeting_bar.pos

    def on_end_meeting(self, instance):
        print("🛑 待ち合わせ終了")
        self.friend_mail = None
        self.meeting_friend_label.text = "相手: （相手未選択）"
        self.meeting_place_label.text = "場所: 未設定"

        if self.app_instance:
            self.app_instance.back_to_map()

    def set_meeting_place(self, place_name):
        self.meeting_place_label.text = f"場所: {place_name}"

    # ========================
    # 既存ロジック
    # ========================
    def initialize_user_location_on_open(self):
        global MY_USER_MAIL
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and isinstance(data, list):
                user_mail = data[0].get("user_mail")
                if user_mail:
                    MY_USER_MAIL = user_mail
                    initialize_user_location(user_mail)
        except Exception as e:
            print("⚠️ init location error:", e)

    def on_friend_button(self, instance):
        if self.app_instance:
            self.app_instance.open_friend_addition()

    def on_chat_button(self, instance):
        if self.app_instance:
            self.app_instance.open_chat_list()

    def on_settings_button(self, instance):
        if self.app_instance:
            self.app_instance.open_settings()

    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat and lon:
            if not self.map_center_updated:
                self.mapview.center_on(lat, lon)
                self.map_center_updated = True
            Clock.schedule_once(lambda dt: self.update_my_marker(lat, lon), 0)

    def on_status(self, stype, status):
        print("📡 GPS status:", stype, status)

    def start_debug_mode(self):
        self.lat = 35.6762
        self.lon = 139.6503
        self.mapview.center_on(self.lat, self.lon)
        self.map_center_updated = True
        Clock.schedule_once(lambda dt: self.update_my_marker(self.lat, self.lon), 1)

    def simulate_location(self, dt):
        self.lat += random.uniform(-0.0003, 0.0003)
        self.lon += random.uniform(-0.0003, 0.0003)
        self.update_my_marker(self.lat, self.lon)

    def update_my_marker(self, lat, lon):
        if self.my_marker:
            self.my_marker.lat = lat
            self.my_marker.lon = lon
        else:
            self.my_marker = MapMarker(lat=lat, lon=lon, source="img/pin.png")
            self.mapview.add_marker(self.my_marker)

        self.lat = lat
        self.lon = lon

    def send_my_location(self, dt):
        if hasattr(self, 'lat') and hasattr(self, 'lon') and MY_USER_MAIL:
            threading.Thread(
                target=lambda: save_my_location((self.lat, self.lon)),
                daemon=True
            ).start()

    def update_friends(self, dt):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return

            user_mail = data[0].get("user_mail")
            if not user_mail:
                return

            friends_mail_list = fetch_friends_by_mail(user_mail)
            for friend_mail in friends_mail_list:
                location = fetch_friend_location(friend_mail)
                if location:
                    lat, lon = location
                    self.update_friend_marker(friend_mail, lat, lon)
        except Exception as e:
            print("⚠️ update_friends error:", e)

    def update_friend_marker(self, friend_mail, lat, lon):
        if friend_mail in self.friend_markers:
            marker = self.friend_markers[friend_mail]
            marker.lat = lat
            marker.lon = lon
        else:
            icon_url = fetch_friend_icon(friend_mail) or "img/cat_placeholder.png"
            marker = FriendMarker(lat, lon, icon_url, friend_mail, self.app_instance)
            self.mapview.add_marker(marker)
            self.friend_markers[friend_mail] = marker


class MyApp(App):
    def build(self):
        request_location_permissions()
        self.main_screen = MainScreen(app_instance=self)
        return self.main_screen

    def open_chat_list(self):
        if hasattr(self, 'main_screen'):
            self.main_screen.friend_update_event.cancel()
            self.main_screen.send_location_event.cancel()

        from chat_screen import MainLayout
        self.root.clear_widgets()
        self.root.add_widget(MainLayout(app_instance=self))

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

    def open_meeting_map(self, friend_mail):
        self.root.clear_widgets()
        self.main_screen = MainScreen(app_instance=self, friend_mail=friend_mail)
        self.root.add_widget(self.main_screen)


if __name__ == '__main__':
    MyApp().run()
