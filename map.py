from kivy.app import App
from kivy_garden.mapview import MapView, MapMarker, MapSource, MapLayer
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image, AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.uix.stencilview import StencilView
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
import random
import requests
import json
import threading
from map_service import (save_my_location, fetch_friends, fetch_friend_icon, 
                        get_friend_mail, fetch_friend_location, initialize_user_location, 
                        fetch_friends_by_mail, get_user_id_by_mail)
from chat_screen import MainLayout  # この行を追加
from settings import SettingsScreen  # この行を追加(settings)
from kivy_garden.mapview import MapMarker
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage
from kivy.graphics import Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from personal_chat_screen import ChatScreen
from kivy.uix.screenmanager import ScreenManager 


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

MY_ID = "cb3cce5a-3ec7-4837-b998-fd9d5446f04a"  # 後方互換性のため
MY_USER_MAIL = None  # 後で設定される

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
# 丸アイコン（Stencil）
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


# ===============================================================
# 友だちマーカー（丸アイコン付き）
# ===============================================================

class FriendMarker(MapMarker):
    def __init__(self, lat, lon, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)

        self.friend_mail = friend_mail
        self.app_instance = app_instance
        self.offset_angle = 0  # アイコンのオフセット角度（度）
        self.offset_distance = 0  # オフセット距離（ピクセル）

        # コンテナ（ボタン + 丸画像）
        self.container = FriendIconButton(
            icon_url=icon_url,
            friend_mail=friend_mail,
            app_instance=app_instance
        )
        self.add_widget(self.container)

        self.bind(pos=self.update_container)
        

    def update_container(self, *args):
        """コンテナの位置を更新（オフセット付き）"""
        import math
        # オフセットがある場合、アイコンの位置をずらす
        if self.offset_distance > 0:
            # ラジアンに変換
            angle_rad = math.radians(self.offset_angle)
            offset_x = self.offset_distance * math.cos(angle_rad)
            offset_y = self.offset_distance * math.sin(angle_rad)
            self.container.pos = (self.pos[0] + offset_x, self.pos[1] + offset_y)
        else:
            self.container.pos = self.pos
    
    def set_icon_offset(self, angle_degrees, distance_pixels):
        """アイコンのオフセットを設定
        
        Args:
            angle_degrees: 度数法での角度（0 = 右、90 = 上）
            distance_pixels: オフセット距離（ピクセル）
        """
        self.offset_angle = angle_degrees
        self.offset_distance = distance_pixels
        self.update_container()
# ===============================================================
# 背景付き画像ボタン
# ===============================================================
class FriendIconButton(ButtonBehavior, FloatLayout):
    def __init__(self, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(**kwargs)

        self.size = (100, 100)
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        # 丸マスク
        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(size=self.size, pos=self.pos)
            StencilUse()

        # アイコン画像
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
        print("🧑 フレンドアイコン押された:", self.friend_mail)
        if self.app_instance:
            self.app_instance.open_friend_profile(self.friend_mail)


class ImageButton(ButtonBehavior, FloatLayout):
    def __init__(self, image_source, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.671,0.905,0.510,1)
            self.bg = RoundedRectangle(size=self.size,pos=self.pos,radius=[12])
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.icon = Image(source=image_source,size_hint=(None,None),size=(50,50),pos_hint={'center_x':0.5,'center_y':0.5})
        self.add_widget(self.icon)
    def _update_bg(self,*args):
        self.bg.size = self.size
        self.bg.pos = self.pos

# ===============================================================
# メイン画面
# ===============================================================
class MainScreen(FloatLayout):
    def __init__(self, app_instance=None, current_user=None, friend_mail=None, **kwargs):  # friend_mail を追加
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.current_user = current_user
        self.friend_mail = friend_mail  # 待ち合わせ相手のfriend_mailを保存
        Window.clearcolor = (1,1,1,1)

        # ユーザーのIDを取得
        self.user_id = current_user.get("user_id") if current_user else None
        print(f"🔍 DEBUG: MainScreen initialized with user_id = {self.user_id}, friend_mail = {self.friend_mail}")

        self.friend_meetings = {}
        self.friend_markers = {}
        self.friend_icons = {}
        self.my_marker = None

        # ログイン時に位置情報を初期化
        self.initialize_user_location_on_open()

        # MapView - 初期座標はGPS取得後に設定
        self.mapview = MapView(lat=35.6762, lon=139.6503, zoom=14, map_source=GSImapSource())  # 初期値：東京都
        self.add_widget(self.mapview)
        self.map_center_updated = False  # マップの中心が更新されたかどうかのフラグ

        # ========================
        # 4つのボタン
        # ========================
        btn_friend = ImageButton(image_source='img/friend.png',
                                 size_hint=(None,None), size=(140,140),
                                 pos_hint={'center_x':0.2, 'y':0.05})
        btn_friend.bind(on_press=self.on_friend_button)
        self.add_widget(btn_friend)

        btn_chat = ImageButton(
            image_source='img/chat.png',
            size_hint=(None,None), size=(140,140),
            pos_hint={'center_x':0.5, 'y':0.05}
        )
        btn_chat.bind(on_press=self.on_chat_button)
        self.add_widget(btn_chat)



        btn_settings = ImageButton(image_source='img/settings.png',
                                   size_hint=(None,None), size=(140,140),
                                   pos_hint={'center_x':0.8, 'y':0.05})
        btn_settings.bind(on_press=self.on_settings_button)
        self.add_widget(btn_settings)

        # ========================
        # GPS / デバッグモード
        # ========================
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

        
        # スケジュールを保存
        # 友人位置情報更新: 5秒 → 15秒（DB読み取り削減）
        # 自分の位置情報送信: 10秒 → 30秒（DB書き込み削減）
        self.friend_update_event = Clock.schedule_interval(self.update_friends, 15)
        self.send_location_event = Clock.schedule_interval(self.send_my_location, 30)
        
        # マップ表示時に1回位置を送信
        Clock.schedule_once(lambda dt: self.send_my_location(dt), 0.5)
        
        if not HAS_GPS:
            # シミュレーション位置情報更新: 3秒ごと（ローカル処理のため影響なし）
            self.location_event = Clock.schedule_interval(self.simulate_location, 3)
    
    def stop_updates(self):
        """画面離脱時に定期処理を停止"""
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
        """Map画面オープン時にユーザーの位置情報をlocationテーブルに初期化し、user_idを取得"""
        global MY_USER_MAIL
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                current_user = data[0]
                user_mail = current_user.get("user_mail")
                if user_mail:
                    MY_USER_MAIL = user_mail
                    
                    # users.json から直接 user_id を取得する場合
                    if "user_id" in current_user:
                        self.user_id = current_user.get("user_id")
                        print(f"🔍 DEBUG: Got user_id from users.json = {self.user_id}")
                    else:
                        # users.json に user_id がない場合は Supabase から取得
                        self.fetch_user_id_from_supabase(user_mail)
                    
                    print(f"🔍 DEBUG: Initializing location for {user_mail}")
                    result = initialize_user_location(user_mail)
                    print(f"🔍 DEBUG: initialize_user_location result = {result}")
        except Exception as e:
            print(f"⚠️ initialize_user_location_on_open error: {e}")
    
    def fetch_user_id_from_supabase(self, user_mail):
        """users.json にuser_idがない場合、Supabase から user_id を取得"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/users"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            params = {"select": "user_id", "user_mail": f"eq.{user_mail}"}
            
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                if data:
                    self.user_id = data[0].get("user_id")
                    print(f"🔍 DEBUG: Got user_id from Supabase = {self.user_id}")
        except Exception as e:
            print(f"⚠️ fetch_user_id_from_supabase error: {e}")
            

    # ======================================
    # 4つのボタン処理
    # ======================================
    def on_friend_button(self, instance):
        print("💬 友達が押されました")
        if self.app_instance:  # この行を追加
            self.app_instance.open_friend_addition()  # この行を追加

    def on_chat_button(self, instance):
        print("💬 チャットボタンが押されました")
        if self.app_instance:  # この行を追加
            self.app_instance.open_chat_list()  # この行を追加

    def on_map_button(self, instance):
        print("🗺️ マップボタンが押されました")

    def on_settings_button(self, instance):
        print("⚙️ 設定ボタンが押されました")
        if self.app_instance:
            self.app_instance.open_settings()


    # ===========================================================
    # GPS / デバッグ
    # ===========================================================
    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat and lon:
            print(f"\n🛰️  [GPS取得] 緯度: {lat:.6f}, 経度: {lon:.6f}")
            # 初回のGPS取得時、マップの中心をここに移動
            if not self.map_center_updated:
                self.mapview.center_on(lat, lon)
                self.map_center_updated = True
                print(f"📍 マップ中心をGPS位置に更新: ({lat}, {lon})")
            Clock.schedule_once(lambda dt: self.update_my_marker(lat, lon), 0)
    def on_status(self, stype, status):
        print(f"📡 GPS status: {stype} - {status}")

    def start_debug_mode(self):
        """デバッグモード開始 - users.json から最後の既知位置を取得するか、デフォルト値を使用"""
        try:
            # users.json から user_mail を取得
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                user_mail = data[0].get("user_mail")
                if user_mail:
                    # Supabase から最後の既知位置を取得
                    url = f"{SUPABASE_URL}/rest/v1/location?select=location&mail=eq.{user_mail}"
                    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                    res = requests.get(url, headers=headers)
                    if res.status_code == 200 and res.json():
                        loc_str = res.json()[0].get("location")
                        if loc_str:
                            lat, lon = map(float, loc_str.strip("{}").split(","))
                            self.lat = lat
                            self.lon = lon
                            print(f"✅ デバッグモード: 最後の位置情報を取得 ({lat}, {lon})")
                            self.mapview.center_on(lat, lon)
                            self.map_center_updated = True
                            Clock.schedule_once(lambda dt:self.update_my_marker(self.lat,self.lon),1)
                            Clock.schedule_interval(self.simulate_location,3)
                            return
        except Exception as e:
            print(f"⚠️ start_debug_mode: {e}")
        
        # フォールバック：デフォルト座標（東京都）を使用
        self.lat = 35.6762
        self.lon = 139.6503
        print(f"💻 デバッグモード: デフォルト座標を使用 ({self.lat}, {self.lon})")
        self.mapview.center_on(self.lat, self.lon)
        self.map_center_updated = True
        Clock.schedule_once(lambda dt:self.update_my_marker(self.lat,self.lon),1)
        Clock.schedule_interval(self.simulate_location,3)
    def simulate_location(self, dt):
        self.lat += random.uniform(-0.0003,0.0003)
        self.lon += random.uniform(-0.0003,0.0003)
        print(f"🔄 [位置情報シミュレート] 緯度: {self.lat:.6f}, 経度: {self.lon:.6f}")
        self.update_my_marker(self.lat,self.lon)

    # ===========================================================
    # 自分マーカー更新
    # ===========================================================
    def update_my_marker(self, lat, lon):
        """マーカーの表示位置を更新（Supabase送信はしない）"""
        if self.my_marker:
            self.my_marker.lat = lat
            self.my_marker.lon = lon
            print(f"🗺️  [マーカー更新] 緯度: {lat:.6f}, 経度: {lon:.6f}")
        else:
            self.my_marker = MapMarker(lat=lat, lon=lon, source="img/pin.png")
            self.mapview.add_marker(self.my_marker)
            print(f"📍 [マーカー作成] 緯度: {lat:.6f}, 経度: {lon:.6f}")
        # 現在の座標を保持
        self.lat = lat
        self.lon = lon

    # ===========================================================
    # 位置情報送信
    # ===========================================================
    def send_my_location(self, dt):
        """現在の位置情報を Supabase に送信（バックグラウンドスレッドで実行）"""
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            if MY_USER_MAIL:
                print(f"\n📤 [位置情報送信開始] ユーザー: {MY_USER_MAIL}, 緯度: {self.lat:.6f}, 経度: {self.lon:.6f}")
                threading.Thread(target=lambda: save_my_location((self.lat, self.lon)), daemon=True).start()
            else:
                print("⚠️ send_my_location: user_mail not available")

    # ===========================================================
    # 友だち情報更新
    # ===========================================================
    def update_friends(self, dt):
        """フレンドの位置情報を更新"""
        try:
            # users.json から user_mail を取得
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or len(data) == 0:
                print("⚠️ update_friends: users.json is empty")
                return
            
            user_mail = data[0].get("user_mail")
            if not user_mail:
                print("⚠️ update_friends: user_mail not found in users.json")
                return
            
            # user_mail から友人のメールアドレスを取得
            friends_mail_list = fetch_friends_by_mail(user_mail)
            print(f"🔍 DEBUG: Found {len(friends_mail_list)} friends for {user_mail}")
            
            # friends_mail_list は既にメールアドレスなので、そのまま使用
            for friend_mail in friends_mail_list:
                print(f"🔍 DEBUG: Friend mail = {friend_mail}")
                location = fetch_friend_location(friend_mail)
                print(f"🔍 DEBUG: Friend {friend_mail} location = {location}")
                if location:
                    lat, lon = location
                    # friend_mailを直接使用してマーカーを更新
                    self.update_friend_marker(friend_mail, lat, lon)
        except Exception as e:
            print(f"⚠️ update_friends error: {e}")





    def update_friend_marker(self, friend_mail, lat, lon):
        """フレンドのマーカーを更新または作成"""
        if friend_mail in self.friend_markers:
            marker = self.friend_markers[friend_mail]
            marker.lat = lat
            marker.lon = lon
        else:
            # friend_mailからfriend_idを取得
            friend_id = get_user_id_by_mail(friend_mail)
            icon_url = fetch_friend_icon(friend_id) or "img/cat_placeholder.png"

            marker = FriendMarker(
                lat, lon, icon_url,
                friend_mail, self.app_instance
            )

            self.mapview.add_marker(marker)
            self.friend_markers[friend_mail] = marker
        
        # 近くのマーカーをチェックしてオフセットを調整
        self.adjust_marker_offsets()
    
    def adjust_marker_offsets(self):
        """近い位置のマーカーを検出し、アイコンをずらす"""
        import math
        
        # 距離の閾値（緯度経度の差で判定）
        DISTANCE_THRESHOLD = 0.0001  # 約10m相当
        
        # オフセットをリセット
        for marker in self.friend_markers.values():
            marker.set_icon_offset(0, 0)
        
        # 自分のマーカーとの距離も確認
        all_markers = list(self.friend_markers.values())
        if self.my_marker:
            all_markers.append(self.my_marker)
        
        # 各マーカーについて、近くのマーカーを検出
        for i, marker in enumerate(all_markers):
            nearby_markers = []
            marker_lat = marker.lat
            marker_lon = marker.lon
            
            for j, other_marker in enumerate(all_markers):
                if i == j:
                    continue
                
                lat_diff = abs(marker_lat - other_marker.lat)
                lon_diff = abs(marker_lon - other_marker.lon)
                
                # 距離が閾値以下の場合は「近い」と判定
                if lat_diff < DISTANCE_THRESHOLD and lon_diff < DISTANCE_THRESHOLD:
                    nearby_markers.append(j)
            
            # 近いマーカーがある場合、このマーカーのアイコンをずらす
            if nearby_markers and isinstance(marker, FriendMarker):
                # マーカーのインデックスに基づいて角度を計算（円形に配置）
                my_index = all_markers.index(marker)
                angle = (my_index * 360 / len(all_markers)) % 360
                distance = 40  # ピクセル単位でのオフセット距離
                marker.set_icon_offset(angle, distance)
                print(f"🎯 [マーカーオフセット] Friend {marker.friend_mail}: 角度 {angle:.1f}°, 距離 {distance}px")  # ← friend_idをfriend_mailに変更

# ===============================================================
# アプリ本体
# ===============================================================
class MyApp(App):
    def build(self):
        request_location_permissions()
        self.main_screen = MainScreen(app_instance=self)  # 変更
        return self.main_screen  # 追加
    
    # 以下を追加
    def open_chat_list(self):
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        """チャット一覧画面を開く"""
        from chat_screen import MainLayout
        self.root.clear_widgets()
        chat_layout = MainLayout(app_instance=self)
        self.root.add_widget(chat_layout)
    
    def open_chat(self, my_id, target_id):  # このメソッドを追加
        """個別チャット画面を開く"""
        from personal_chat_screen import ChatScreen
        self.root.clear_widgets()
        chat_screen = ChatScreen(my_id, target_id, app_instance=self)
        self.root.add_widget(chat_screen)
        
    def back_to_list(self):  # このメソッドも追加（チャットからリストに戻る用）
        """チャット一覧に戻る"""
        self.open_chat_list()
    
            
    def open_friend_addition(self):
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        from addition import FriendApp
        self.root.clear_widgets()
        screen = FriendApp()
        self.root.add_widget(screen)
            
    def back_to_map(self):
        """マップ画面に戻る"""
        # 現在の画面がChatScreenなら停止
        if hasattr(self.root, 'children'):
            for child in self.root.children:
                if isinstance(child, ChatScreen):
                    child.stop_updates()
        
        self.root.clear_widgets()
        self.main_screen = MainScreen(app_instance=self)
        self.root.add_widget(self.main_screen)
        

    def open_settings(self):  # このメソッドを追加
        """設定画面を開く"""
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        from settings import SettingsScreen
        self.root.clear_widgets()
        settings_screen = SettingsScreen(app_instance=self)
        self.root.add_widget(settings_screen)
        
    def open_friend_profile(self, friend_mail):
        """フレンドプロフィール画面を開く"""
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        from friend_profile import FriendProfileScreen  # friend_profile.pyからインポート
        self.root.clear_widgets()
        profile_screen = FriendProfileScreen(friend_mail=friend_mail, app_instance=self)
        self.root.add_widget(profile_screen)
    
    def open_meeting_map(self, friend_mail):
        """待ち合わせ用のマップ画面を開く"""
        # 定期処理を停止
        print(f"🗺️ 友人 {friend_mail} との待ち合わせ場所を指定してください")
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        self.root.clear_widgets()
        from map2 import MainScreen2
        self.main_screen = MainScreen2(app_instance=self, friend_mail=friend_mail)
        
        self.root.add_widget(self.main_screen)
        print(f"🗺️ 友人 {friend_mail} との待ち合わせ場所を指定してください")
        
    def on_end_meeting(self, instance):
        """待ち合わせ終了ボタン - meeting_sharesとmeetingsのstatusをfalseにしてmap.pyへ戻る"""
        print("🛑 待ち合わせ終了")
        
        try:
            # users.jsonからメールアドレスを取得
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            user_mail = data[0].get("user_mail") if isinstance(data, list) else data.get("user_mail")
            
            if user_mail:
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Step 1: meeting_sharesから自分のアクティブなmeeting_idを取得
                url_shares = f"{SUPABASE_URL}/rest/v1/meeting_shares"
                params = {
                    "select": "meeting_id",
                    "user_mail": f"eq.{user_mail}",
                    "status": "eq.true"
                }
                
                res = requests.get(url_shares, headers=headers, params=params)
                if res.status_code == 200 and res.json():
                    meeting_id = res.json()[0].get("meeting_id")
                    print(f"📍 アクティブなmeeting_id: {meeting_id}")
                    
                    # Step 2: meeting_sharesのstatusをfalseに更新（該当するmeeting_idの全レコード）
                    update_data = {"status": False}
                    params_update = {"meeting_id": f"eq.{meeting_id}"}
                    
                    res_shares = requests.patch(url_shares, headers=headers, params=params_update, data=json.dumps(update_data))
                    if res_shares.status_code in (200, 204):
                        print("✅ meeting_shares のステータスを更新しました")
                    else:
                        print(f"⚠️ meeting_shares 更新失敗: {res_shares.status_code}")
                    
                    # Step 3: meetingsテーブルのstatusもfalseに更新
                    url_meetings = f"{SUPABASE_URL}/rest/v1/meetings"
                    params_meetings = {"id": f"eq.{meeting_id}"}
                    
                    res_meetings = requests.patch(url_meetings, headers=headers, params=params_meetings, data=json.dumps(update_data))
                    if res_meetings.status_code in (200, 204):
                        print("✅ meetings のステータスを更新しました")
                    else:
                        print(f"⚠️ meetings 更新失敗: {res_meetings.status_code}")
                else:
                    print("⚠️ アクティブなミーティングが見つかりません")
            
        except Exception as e:
            print(f"❌ on_end_meeting error: {e}")
            import traceback
            traceback.print_exc()
        
        # map.pyへ戻る
        if self.app:
            if isinstance(self.app.root, ScreenManager):
                print("🔄 ScreenManager経由でmap画面へ遷移")
                self.app.root.current = "map"
            else:
                print("🔄 back_to_map()でmap画面へ遷移")
                self.app.back_to_map()
    

if __name__ == '__main__':
    MyApp().run()
