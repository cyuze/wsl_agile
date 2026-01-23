from kivy.app import App
from kivy_garden.mapview import MapView, MapMarker, MapSource, MapLayer
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image, AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, Line
from kivy.uix.stencilview import StencilView
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
import random
import requests
import json
import threading
from map_2_service import (
    save_my_location,
    fetch_friends,
    fetch_friend_icon,
    get_friend_mail,
    fetch_friend_location,
    initialize_user_location,
    fetch_friends_by_mail,
    get_user_id_by_mail,
)

# 日本語フォント登録
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

# ===============================================================
# Supabase 設定
# ===============================================================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

MY_ID = "cb3cce5a-3ec7-4837-b998-fd9d5446f04a"
MY_USER_MAIL = None

# GPS 判定
try:
    from plyer import gps
    HAS_GPS = True
except ImportError:
    HAS_GPS = False

# ===============================================================
# 地理院地図
# ===============================================================
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

# ===============================================================
# 場所指定マーカー（緑のピン）
# ===============================================================
class LocationMarker(MapMarker):
    def __init__(self, lat, lon, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)
        
        container = FloatLayout(size=(80, 80))
        pin_image = Image(
            source='img/pin.png',
            size_hint=(None, None),
            size=(80, 80),
            allow_stretch=True
        )
        container.add_widget(pin_image)
        self.add_widget(container)
        self.bind(pos=lambda instance, value: setattr(container, 'pos', value))

# ===============================================================
# 経路レイヤー
# ===============================================================
class RouteLayer(MapLayer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.routes = []
    
    def add_route(self, start_lat, start_lon, end_lat, end_lon, color=(0, 0.5, 1, 0.8)):
        self.routes.append((start_lat, start_lon, end_lat, end_lon, color))
        self.reposition()
    
    def clear_routes(self):
        self.routes = []
        self.canvas.clear()
    
    def reposition(self):
        self.canvas.clear()
        if not self.routes:
            return
        mapview = self.parent
        if not mapview:
            return
        with self.canvas:
            for start_lat, start_lon, end_lat, end_lon, color in self.routes:
                start_x, start_y = mapview.get_window_xy_from(start_lat, start_lon, mapview.zoom)
                end_x, end_y = mapview.get_window_xy_from(end_lat, end_lon, mapview.zoom)
                Color(*color)
                Line(points=[start_x, start_y, end_x, end_y], width=3)

# ===============================================================
# 友だちマーカー
# ===============================================================
class CircleImageView(ButtonBehavior, StencilView):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        self.img = AsyncImage(source=self.source, allow_stretch=True, keep_ratio=False, size=self.size)
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

class FriendMarker(MapMarker):
    def __init__(self, lat, lon, icon_url, friend_id, app_instance, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)
        self.friend_id = friend_id
        self.app_instance = app_instance
        self.container = FriendIconButton(
            icon_url=icon_url,
            friend_id=friend_id,
            app_instance=app_instance
        )
        self.add_widget(self.container)
        self.bind(pos=self.update_container)

    def update_container(self, *args):
        self.container.pos = self.pos

class FriendIconButton(ButtonBehavior, FloatLayout):
    def __init__(self, icon_url, friend_id, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.size = (100, 100)
        self.friend_id = friend_id
        self.app_instance = app_instance

        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(size=self.size, pos=self.pos)
            StencilUse()

        self.image = AsyncImage(
            source=icon_url,
            allow_stretch=True,
            keep_ratio=False,
            size=self.size,
        )
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
        print("🧑 フレンドアイコン押された:", self.friend_id)
        if self.app_instance:
            self.app_instance.open_friend_profile(self.friend_id)

# ===============================================================
# メイン画面
# ===============================================================
class MainScreen(FloatLayout):
    def __init__(self, app_instance=None, current_user=None, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.current_user = current_user
        Window.clearcolor = (1,1,1,1)

        self.user_id = current_user.get("user_id") if current_user else None
        print(f"🔍 DEBUG: MainScreen initialized with user_id = {self.user_id}")

        self.friend_meetings = {}
        self.friend_markers = {}
        self.friend_icons = {}
        self.my_marker = None
        self.location_marker = None
        self.is_location_mode = False
        self.current_friend_id = None
        self.selected_location = None
        self.route_layer = None
        self.location_bg = None

        self.initialize_user_location_on_open()

        # MapView
        self.mapview = MapView(lat=39.701083, lon=141.136132, zoom=14, map_source=GSImapSource())
        self.add_widget(self.mapview)
        
        # 経路レイヤーを追加
        self.route_layer = RouteLayer()
        self.mapview.add_layer(self.route_layer)
        
        # 場所指定UI作成
        self.create_location_mode_ui()

        # GPS起動
        if HAS_GPS:
            try:
                gps.configure(on_location=self.on_location, on_status=self.on_status)
                gps.start()
                print("📡 GPSモードで起動")
            except NotImplementedError:
                print("⚠️ GPSなし → デバッグモードへ")
                self.start_debug_mode()
        else:
            print("💻 デバッグモード開始")
            self.start_debug_mode()

        self.friend_update_event = Clock.schedule_interval(self.update_friends, 5)
        self.send_location_event = Clock.schedule_interval(self.send_my_location, 10)
        Clock.schedule_once(lambda dt: self.send_my_location(dt), 0.5)
        
        if not HAS_GPS:
            self.location_event = Clock.schedule_interval(self.simulate_location, 3)
    
    def create_location_mode_ui(self):
        """場所指定モード用のUIを作成"""
        # 白い背景パネル
        self.location_bg = FloatLayout(
            size_hint=(None, None),
            size=(Window.width * 0.92, Window.height * 0.88),
            pos=(Window.width * 0.04, Window.height * 0.06),
            opacity=1
        )
        with self.location_bg.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.bg_rect = RoundedRectangle(
                pos=self.location_bg.pos,
                size=self.location_bg.size,
                radius=[20]
            )
        self.location_bg.bind(
            pos=lambda i, v: setattr(self.bg_rect, 'pos', v),
            size=lambda i, v: setattr(self.bg_rect, 'size', v)
        )
        self.add_widget(self.location_bg)
        
        # タイトル
        self.location_title = Label(
            text='場所指定画面 1',
            font_name='NotoSansJP',
            font_size='18sp',
            color=(0.4, 0.6, 0.8, 1),
            size_hint=(None, None),
            size=(Window.width * 0.84, 40),
            pos=(Window.width * 0.08, Window.height * 0.90),
            halign='left',
            valign='middle'
        )
        self.location_title.bind(size=self.location_title.setter('text_size'))
        self.add_widget(self.location_title)
        
        # 青い枠（マップエリア）
        self.location_frame = FloatLayout(
            size_hint=(None, None),
            size=(Window.width * 0.84, Window.height * 0.62),
            pos=(Window.width * 0.08, Window.height * 0.26),
            opacity=1
        )
        with self.location_frame.canvas.before:
            Color(0.2, 0.6, 1, 1)
            self.frame_line = Line(
                rectangle=(
                    self.location_frame.x,
                    self.location_frame.y,
                    self.location_frame.width,
                    self.location_frame.height
                ),
                width=4
            )
        self.location_frame.bind(
            pos=self._update_frame_line,
            size=self._update_frame_line
        )
        self.add_widget(self.location_frame)
        
        # マップを枠内に配置
        self.attach_mapview_to_frame()
        
        # 中央のテキスト
        self.location_text = Label(
            text='場所を指定する',
            font_name='NotoSansJP',
            font_size='20sp',
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(Window.width, 50),
            pos=(0, Window.height * 0.18)
        )
        self.add_widget(self.location_text)
        
        # 下部のボタン
        button_container = FloatLayout(
            size_hint=(None, None),
            size=(Window.width * 0.84, 70),
            pos=(Window.width * 0.08, Window.height * 0.08)
        )
        
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(Window.width * 0.6, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=30
        )
        
        # 指定するボタン
        specify_btn = Button(
            text='指定する',
            font_name='NotoSansJP',
            font_size='16sp',
            size_hint_x=0.5,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        with specify_btn.canvas.before:
            Color(0.7, 0.9, 0.6, 1)
            specify_btn.bg_rect = RoundedRectangle(
                pos=specify_btn.pos,
                size=specify_btn.size,
                radius=[15]
            )
        specify_btn.bind(
            pos=lambda i, v: setattr(specify_btn.bg_rect, 'pos', i.pos),
            size=lambda i, v: setattr(specify_btn.bg_rect, 'size', i.size),
            on_press=lambda i: self.on_location_select()
        )
        
        # 共有するボタン
        share_btn = Button(
            text='共有する',
            font_name='NotoSansJP',
            font_size='16sp',
            size_hint_x=0.5,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        with share_btn.canvas.before:
            Color(0.7, 0.9, 0.6, 1)
            share_btn.bg_rect = RoundedRectangle(
                pos=share_btn.pos,
                size=share_btn.size,
                radius=[15]
            )
        share_btn.bind(
            pos=lambda i, v: setattr(share_btn.bg_rect, 'pos', i.pos),
            size=lambda i, v: setattr(share_btn.bg_rect, 'size', i.size),
            on_press=lambda i: self.on_location_share()
        )
        
        button_layout.add_widget(specify_btn)
        button_layout.add_widget(share_btn)
        button_container.add_widget(button_layout)
        
        self.location_buttons = button_container
        self.add_widget(self.location_buttons)
        
        # UIを最前面に
        self.is_location_mode = True
    
    def _update_frame_line(self, *args):
        if self.location_frame:
            self.frame_line.rectangle = (
                self.location_frame.x,
                self.location_frame.y,
                self.location_frame.width,
                self.location_frame.height
            )
    
    def attach_mapview_to_frame(self):
        """マップを場所指定用の枠内に配置"""
        if not (self.location_frame and self.mapview):
            return

        if self.mapview.parent is self:
            self.remove_widget(self.mapview)
            self.location_frame.add_widget(self.mapview)

        self.mapview.size_hint = (None, None)
        self._update_mapview_layout()
        self.location_frame.bind(pos=self._update_mapview_layout, size=self._update_mapview_layout)

    def _update_mapview_layout(self, *args):
        if not (self.location_frame and self.mapview):
            return
        margin = 6
        self.mapview.size = (
            max(0, self.location_frame.width - margin * 2),
            max(0, self.location_frame.height - margin * 2)
        )
        self.mapview.pos = (
            self.location_frame.x + margin,
            self.location_frame.y + margin
        )
    
    def on_touch_down(self, touch):
        """タッチイベントを処理"""
        if self.is_location_mode:
            print(f"🖱️ Touch at ({touch.x}, {touch.y})")
            
            # ボタン領域
            if self.location_buttons and self.location_buttons.collide_point(*touch.pos):
                print("⚠️ ボタン領域")
                return super().on_touch_down(touch)

            # 枠外は無視
            if self.location_frame and not self.location_frame.collide_point(*touch.pos):
                return super().on_touch_down(touch)
            
            # マップ領域
            if self.mapview and self.mapview.collide_point(*touch.pos):
                if not touch.is_double_tap:
                    lat, lon = self.mapview.get_latlon_at(touch.x, touch.y)
                    print(f"📍 マップタップ: lat={lat}, lon={lon}")
                    Clock.schedule_once(lambda dt: self.set_meeting_location(lat, lon), 0.1)
                    return True
        
        return super().on_touch_down(touch)
    
    def set_meeting_location(self, lat, lon):
        """待ち合わせ場所を設定"""
        if self.location_marker:
            self.mapview.remove_marker(self.location_marker)
        
        self.location_marker = LocationMarker(lat=lat, lon=lon)
        self.mapview.add_marker(self.location_marker)
        self.selected_location = (lat, lon)
        self.show_routes_to_location(lat, lon)
        print(f"✅ 待ち合わせ場所設定: ({lat}, {lon})")
    
    def show_routes_to_location(self, dest_lat, dest_lon):
        """経路を表示"""
        if not self.route_layer:
            return
        
        self.route_layer.clear_routes()
        
        # 自分の経路（青）
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            self.route_layer.add_route(
                self.lat, self.lon,
                dest_lat, dest_lon,
                color=(0, 0.5, 1, 0.8)
            )
            print(f"🔵 自分の経路")
        
        # 友達の経路（緑）
        if self.current_friend_id and self.current_friend_id in self.friend_markers:
            friend_marker = self.friend_markers[self.current_friend_id]
            self.route_layer.add_route(
                friend_marker.lat, friend_marker.lon,
                dest_lat, dest_lon,
                color=(0, 1, 0, 0.8)
            )
            print(f"🟢 友達の経路")
    
    def on_location_select(self):
        """指定するボタン"""
        if self.selected_location:
            print(f"📍 場所を指定: {self.selected_location}")
        else:
            print("⚠️ 場所を選択してください")
    
    def on_location_share(self):
        """共有するボタン"""
        if self.selected_location:
            lat, lon = self.selected_location
            print(f"✅ 待ち合わせ場所共有: ({lat}, {lon})")
            # TODO: Supabaseに保存
        else:
            print("⚠️ 場所が選択されていません")
    
    # 以下、既存のメソッド
    def stop_updates(self):
        if hasattr(self, 'friend_update_event'):
            self.friend_update_event.cancel()
        if hasattr(self, 'send_location_event'):
            self.send_location_event.cancel()
        if hasattr(self, 'location_event'):
            self.location_event.cancel()
        if HAS_GPS:
            try:
                gps.stop()
            except:
                pass

    def initialize_user_location_on_open(self):
        global MY_USER_MAIL
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                current_user = data[0]
                user_mail = current_user.get("user_mail")
                if user_mail:
                    MY_USER_MAIL = user_mail
                    if "user_id" in current_user:
                        self.user_id = current_user.get("user_id")
                    else:
                        self.fetch_user_id_from_supabase(user_mail)
                    result = initialize_user_location(user_mail)
        except Exception as e:
            print(f"⚠️ initialize_user_location_on_open error: {e}")
    
    def fetch_user_id_from_supabase(self, user_mail):
        try:
            url = f"{SUPABASE_URL}/rest/v1/users"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            params = {"select": "user_id", "user_mail": f"eq.{user_mail}"}
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                if data:
                    self.user_id = data[0].get("user_id")
        except Exception as e:
            print(f"⚠️ fetch_user_id_from_supabase error: {e}")

    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat and lon:
            Clock.schedule_once(lambda dt: self.update_my_marker(lat, lon), 0)
    
    def on_status(self, stype, status):
        print(f"📡 GPS status: {stype} - {status}")

    def start_debug_mode(self):
        self.lat = 39.701083
        self.lon = 141.136132
        Clock.schedule_once(lambda dt:self.update_my_marker(self.lat,self.lon),1)
        Clock.schedule_interval(self.simulate_location,3)
    
    def simulate_location(self, dt):
        self.lat += random.uniform(-0.0003,0.0003)
        self.lon += random.uniform(-0.0003,0.0003)
        self.update_my_marker(self.lat,self.lon)

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
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            if MY_USER_MAIL:
                threading.Thread(target=lambda: save_my_location((self.lat, self.lon)), daemon=True).start()

    def update_friends(self, dt):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or len(data) == 0:
                return
            user_mail = data[0].get("user_mail")
            if not user_mail:
                return
            friends_mail_list = fetch_friends_by_mail(user_mail)
            for friend_mail in friends_mail_list:
                location = fetch_friend_location(friend_mail)
                if location:
                    lat, lon = location
                    friend_user_id = get_user_id_by_mail(friend_mail)
                    if friend_user_id:
                        self.update_friend_marker(friend_user_id, lat, lon)
        except Exception as e:
            print(f"⚠️ update_friends error: {e}")

    def update_friend_marker(self, friend_id, lat, lon):
        if friend_id in self.friend_markers:
            marker = self.friend_markers[friend_id]
            marker.lat = lat
            marker.lon = lon
        else:
            icon_url = fetch_friend_icon(friend_id) or "img/cat_placeholder.png"
            marker = FriendMarker(lat, lon, icon_url, friend_id, self.app_instance)
            self.mapview.add_marker(marker)
            self.friend_markers[friend_id] = marker