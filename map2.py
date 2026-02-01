# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage, Image
from kivy.uix.behaviors import ButtonBehavior
from kivy_garden.mapview import MapView, MapMarker, MapSource
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex

from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
import random
import json
import threading
import requests

# ========= あなたの外部サービス =========
# 既存のまま利用（存在しない場合は必要箇所をコメントアウトして利用してください）
from map_service import (
    save_my_location, fetch_friends_by_mail,
    fetch_friend_location, fetch_friend_icon, initialize_user_location
)
from map_service import get_user_id_by_mail
from map_2_service import save_meeting, save_meeting_shares, check_meeting_shares_status

# ========= フォントと背景色 =========
LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236/255, 244/255, 232/255, 1)  # #ECF4E8

# ========= UI スケールユーティリティ =========
scale = Window.dpi / 120.0
def Sdp(v): return dp(v * scale)
def Ssp(v): return sp(v * scale)

# ========= Android 権限 =========
try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False

def request_location_permissions():
    if ANDROID:
        request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION])

# ========= GPS 有無 =========
try:
    from plyer import gps
    HAS_GPS = True
except ImportError:
    HAS_GPS = False

# ========= Supabase（必要な人だけ使います） =========
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"
MY_USER_MAIL = None

# ========= 地理院地図 =========
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
    """薄い緑の角丸ボタン（押下で色が少し濃くなる）"""
    def __init__(self, image_source='', text='', **kwargs):
        super().__init__(**kwargs)
        # 少しだけくすんだ薄緑 → スクショの雰囲気に近づける
        self.normal_color = get_color_from_hex('#CFE9C7')  # 旧: #D1EFC7
        self.down_color   = get_color_from_hex('#B9DBAE')  # 旧: #BFE4B0

        with self.canvas.before:
            Color(*self.normal_color)
            # 角丸を少し強めに（丸っこく）
            self.bg = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(26)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        if text:
            self.label = Label(
                text=text, size_hint=(1, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                font_size=Ssp(16), font_name="Japanese",
                bold=True, color=(0, 0, 0, 1)
            )
            self.add_widget(self.label)
        elif image_source:
            self.icon = Image(
                source=image_source, size_hint=(None, None),
                size=(Sdp(48), Sdp(48)),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(self.icon)

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def on_press(self):
        with self.canvas.before:
            Color(*self.down_color)
            self.bg = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(26)])

    def on_release(self):
        with self.canvas.before:
            Color(*self.normal_color)
            self.bg = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(26)])

# ========= 丸アイコン（友だち用） =========
class FriendIconButton(ButtonBehavior, FloatLayout):
    def __init__(self, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.size = (Sdp(56), Sdp(56))
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        with self.canvas.before:
            # 外枠（薄い緑）
            Color(*get_color_from_hex('#D1EFC7'))
            self.outer = Ellipse(
                size=(self.size[0] + Sdp(8), self.size[1] + Sdp(8)),
                pos=(self.pos[0] - Sdp(4), self.pos[1] - Sdp(4))
            )
            StencilPush()
            self.mask = Ellipse(size=self.size, pos=self.pos)
            StencilUse()

        self.image = AsyncImage(
            source=icon_url or "img/cat_placeholder.png",
            allow_stretch=True, keep_ratio=False, size=self.size
        )
        self.add_widget(self.image)

        with self.canvas.after:
            StencilUnUse()
            StencilPop()

        self.bind(pos=self._update_mask, size=self._update_mask)

    def _update_mask(self, *args):
        self.mask.pos = self.pos
        self.mask.size = self.size
        self.image.pos = self.pos
        self.image.size = self.size
        self.outer.pos = (self.pos[0] - Sdp(4), self.pos[1] - Sdp(4))
        self.outer.size = (self.size[0] + Sdp(8), self.size[1] + Sdp(8))

    def on_press(self):
        if self.app_instance and hasattr(self.app_instance, 'open_friend_profile'):
            self.app_instance.open_friend_profile(self.friend_mail)

class FriendMarker(MapMarker):
    def __init__(self, lat, lon, icon_url, friend_mail, app_instance, **kwargs):
        super().__init__(lat=lat, lon=lon, **kwargs)
        self.friend_mail = friend_mail
        self.app_instance = app_instance
        self.offset_angle = 0
        self.offset_distance = 0

        self.container = FriendIconButton(
            icon_url=icon_url, friend_mail=friend_mail, app_instance=app_instance
        )
        self.add_widget(self.container)
        self.bind(pos=self._update_container)

    def _update_container(self, *args):
        # シンプルにマーカー位置へ追従（必要に応じてオフセット）
        self.container.pos = (self.pos[0], self.pos[1])

    def set_icon_offset(self, angle_degrees, distance_pixels):
        # 今回は未使用（必要ならオフセット制御を追加）
        self.offset_angle = angle_degrees
        self.offset_distance = distance_pixels
        self._update_container()

# ========= メイン画面 =========
class MainScreen2(Screen):
    """
    ・マップは全面表示（size_hint=(1,1)）
    ・下部に「薄い緑の帯（オーバーレイ）」＋「指定する／共有する」丸角ボタン
    ・帯の中にタイトル「場所を指定する」と、選択住所の表示欄
    """
    def __init__(self, app_instance=None, current_user=None, friend_mail=None, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.current_user = current_user
        self.friend_mail = friend_mail

        self.user_id = current_user.get("user_id") if current_user else None
        self.is_selecting_location = False
        self.selected_location_info = None

        # ルートレイヤ（重ね順を制御）
        self.root_layer = FloatLayout()
        self.add_widget(self.root_layer)

        # ---- MapView（全面表示） ----
        self.mapview = MapView(lat=35.6762, lon=139.6503, zoom=14, map_source=GSImapSource())
        self.mapview.size_hint = (1, 1)
        self.mapview.pos_hint = {'x': 0, 'y': 0}
        self.mapview.bind(on_touch_down=self.on_map_touch)
        self.root_layer.add_widget(self.mapview)  # 先に追加＝下層

        # ---- 下部の薄い緑パネル（帯：オーバーレイ）----
        self._build_bottom_bar()

        # ---- 位置情報初期化 & GPS/デバッグ ----
        self._initialize_user_location_on_open()
        self.map_center_updated = False
        if HAS_GPS:
            try:
                gps.configure(on_location=self.on_location, on_status=self.on_status)
                gps.start()
            except NotImplementedError:
                self._start_debug_mode()
        else:
            self._start_debug_mode()

        # ---- 定期処理（DBアクセス負荷を下げる間隔）----
        self.friend_markers = {}
        self.my_marker = None

        # 友だち位置更新
        self.friend_update_event = Clock.schedule_interval(self.update_friends, 15)
        # 自分位置送信
        self.send_location_event = Clock.schedule_interval(self.send_my_location, 30)
        # 起動直後に1回送信
        Clock.schedule_once(self.send_my_location, 0.5)

        if not HAS_GPS:
            # ローカルシミュレーション
            self.location_event = Clock.schedule_interval(self._simulate_location, 3)

        # Android 戻るボタン
        Window.bind(on_keyboard=self._on_back_button)

    # ---------- UI 構築：下部バー ----------
    def _build_bottom_bar(self):
        self.bottom_bar = FloatLayout(size_hint=(1, None), height=dp(160), pos_hint={'x': 0, 'y': 0})
        with self.bottom_bar.canvas.before:
            Color(*get_color_from_hex('#ECF4E8'))  # とても薄い緑
            self.bottom_bg = RoundedRectangle(
                size=self.bottom_bar.size, pos=self.bottom_bar.pos,
                radius=[dp(24), dp(24), 0, 0]  # 上だけ角丸
            )
        self.bottom_bar.bind(
            size=lambda *_: setattr(self.bottom_bg, 'size', self.bottom_bar.size),
            pos=lambda *_: setattr(self.bottom_bg, 'pos', self.bottom_bar.pos),
        )

        # タイトル（帯内上部）
        self.bottom_title = Label(
            text='場所を指定する', font_name="Japanese", font_size=Ssp(18), bold=True,
            color=(0, 0, 0, 1), size_hint=(None, None),
            size=(self.bottom_bar.width, dp(36)),
            pos_hint={'center_x': 0.5, 'y': 0.60}
        )
        def _sync_title_size(*_):
            self.bottom_title.size = (self.bottom_bar.width, dp(36))
        self.bottom_bar.add_widget(self.bottom_title)
        self.bottom_bar.bind(size=_sync_title_size)

        # 選択中の住所・施設名のスクロール表示（帯内中段）
        info_scroll = ScrollView(
            size_hint=(0.94, None), height=dp(40),
            pos_hint={'center_x': 0.5, 'y': 0.38}, do_scroll_x=True, do_scroll_y=False
        )
        self.location_info_label = Label(
            text='', font_name="Japanese", font_size=Ssp(14), color=(0, 0, 0, 1),
            size_hint_x=None, size_hint_y=1, width=2000, text_size=(1900, None)
        )
        info_scroll.add_widget(self.location_info_label)
        self.bottom_bar.add_widget(info_scroll)

        # ボタン（帯内下段）
        btn_specify = ImageButton(
            text='指定する', size_hint=(None, None), size=(Sdp(140), Sdp(56)),
            pos_hint={'x': 0.08, 'y': 0.08}
        )
        btn_specify.bind(on_press=self.on_specify_button)
        self.bottom_bar.add_widget(btn_specify)

        btn_share = ImageButton(
            text='共有する', size_hint=(None, None), size=(Sdp(140), Sdp(56)),
            pos_hint={'right': 0.92, 'y': 0.08}
        )
        btn_share.bind(on_press=self.on_share_button)
        self.bottom_bar.add_widget(btn_share)

        # MapView の後に追加＝オーバーレイで上に来る
        self.root_layer.add_widget(self.bottom_bar)

    # ---------- 位置選択フロー ----------
    def on_specify_button(self, *_):
        self.is_selecting_location = not self.is_selecting_location
        if self.is_selecting_location:
            self.location_info_label.text = "マップをタップして場所を指定してください"
        else:
            self.location_info_label.text = ""

    def on_share_button(self, *_):
        self.is_selecting_location = False
        # 位置選択済みか確認
        if not self.selected_location_info:
            self.location_info_label.text = "⚠️ まず場所をタップして指定してください"
            return

        if len(self.selected_location_info) == 3:
            lat, lon, building_name = self.selected_location_info
        else:
            lat, lon = self.selected_location_info
            building_name = None

        threading.Thread(
            target=self._share_meeting_location, args=(lat, lon, building_name), daemon=True
        ).start()

    def _share_meeting_location(self, lat, lon, building_name=None):
        try:
            # users.json から自分のメール
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                my_mail = data[0].get("user_mail")
            else:
                my_mail = data.get("user_mail")
            if not my_mail:
                print("⚠️ user_mail が取得できません")
                return

            meeting_id = save_meeting(lat, lon, building_name)
            
            print(f"📧 my_mail = {my_mail}")
            print(f"🏢 building_name = {building_name}")
            
            # 1. meetingsテーブルに保存（ホストのメールアドレスを追加）
            print(f"📍 Step 1: Saving to meetings table...")
            meeting_id = save_meeting(lat, lon, building_name, host_mail=my_mail)  # ← host_mailを追加
            if not meeting_id:
                print("⚠️ meetings への保存に失敗")
                return

            
            self.meeting_id = meeting_id 
            
            print(f"✅ Step 1 Complete: meeting_id = {meeting_id}")
            
            # 2. meeting_sharesテーブルに自分のメールを保存
            print(f"📍 Step 2: Saving to meeting_shares (my_mail)...")
            if not save_meeting_shares(my_mail, meeting_id):
                print("⚠️ meeting_shares（自分）保存失敗")
                return

            # 現在選択中のフレンド（メール）があれば共有
            if self.friend_mail:
                save_meeting_shares(self.friend_mail, meeting_id)

            has_active = check_meeting_shares_status(my_mail)
            Clock.schedule_once(lambda dt: self._navigate_after_share(has_active), 0)
        except Exception as e:
            print(f"⚠️ _share_meeting_location error: {e}")

    def _navigate_after_share(self, has_active_meeting: bool):
        # あなたのアプリの画面遷移ポリシーに合わせて調整
        # ここでは map（この画面）に留まる想定。必要なら app_instance.root.current を切り替え。
        if has_active_meeting:
            print("✅ meeting_shares に共有済み（アクティブ）")
            print("🔄 アクティブなミーティングがあります → map3.pyへ移動")
            if self.app_instance:
                try:
                    # meeting_idを渡してmap3を開く
                    if hasattr(self, 'meeting_id'):
                        print(f"📍 meeting_id = {self.meeting_id} を渡してmap3を開きます")
                        self.app_instance.open_map3(meeting_id=self.meeting_id)
                    else:
                        print("⚠️ meeting_id が見つかりません")
                except Exception as e:
                    print(f"❌ open_map3 呼び出しエラー: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print("🔄 map.pyへ戻ります")
            if self.app_instance:
                # ScreenManagerを使用して遷移
                if isinstance(self.app_instance.root, ScreenManager):
                    self.app_instance.root.current = "map"
                else:
                    # フォールバック
                    self.app_instance.back_to_map()
    
    def on_back_button(self, window, key, *args):
        """ESCキーまたはAndroidの戻るボタン処理"""
        # key=27 が ESC / Android 戻るボタン
        if key != 27:
            return False
        
        print("[DEBUG] map2.py on_back_button called")
        
        if self.manager:
            # 前の画面（フレンドプロフィール）に戻る
            try:
                # friend_profileスクリーンを探して戻る
                for screen in self.manager.screens:
                    if 'friend_profile' in screen.name:
                        self.manager.current = screen.name
                        return True
            except:
                pass
        
        # フォールバック：親のback_to_mapメソッドを使用
        if self.app_instance and hasattr(self.app_instance, 'back_to_map'):
            self.app_instance.back_to_map()
            return True
        
        return False
    
    def on_leave(self):
        """画面を離脱するときにキーボードイベントのバインドを解除"""
        try:
            Window.unbind(on_keyboard=self.on_back_button)
        except:
            pass

    # ---------- マップタップで位置取得 ----------
    def on_map_touch(self, mapview, touch):
        # 場所指定モード時のみ
        if not self.is_selecting_location:
            return False
        # MapView 上のタップか？
        if not mapview.collide_point(*touch.pos):
            return False
        # 地理座標に変換
        lat, lon = mapview.get_latlon_at(touch.pos[0], touch.pos[1])
        # 住所取得（Nominatim）
        Clock.schedule_once(lambda dt: self._fetch_location_info(lat, lon), 0)
        return True

    def _fetch_location_info(self, lat, lon):
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {"format": "json", "lat": lat, "lon": lon, "language": "ja"}
            headers = {"User-Agent": "MeetingApp/1.0"}
            res = requests.get(url, params=params, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                address = data.get('address', {})
                info_parts = []
                if 'state' in address:
                    info_parts.append(address['state'])
                if 'city' in address:
                    info_parts.append(address['city'])
                elif 'county' in address:
                    info_parts.append(address['county'])
                if 'suburb' in address:
                    info_parts.append(address['suburb'])

                building_name = None
                if 'name' in data and data['name'] != address.get('city'):
                    info_parts.append(data['name'])
                    building_name = data['name']

                info_text = " / ".join(info_parts) if info_parts else f"座標: {lat:.6f}, {lon:.6f}"
                self.location_info_label.text = info_text
                self.selected_location_info = (lat, lon, building_name)

                # マーカー表示
                self._update_my_marker(lat, lon, pin_source="img/pin.png")
            else:
                self.location_info_label.text = f"座標: {lat:.6f}, {lon:.6f}"
                self.selected_location_info = (lat, lon, None)
        except Exception as e:
            self.location_info_label.text = f"エラー: {str(e)}"
            self.selected_location_info = (lat, lon, None)

    # ---------- GPS / デバッグ ----------
    def on_location(self, **kwargs):
        # 柔軟に緯度経度キーを受け取る
        lat = kwargs.get("lat") if kwargs.get("lat") is not None else kwargs.get("latitude")
        lon = kwargs.get("lon") if kwargs.get("lon") is not None else kwargs.get("longitude")

        # plyer は文字列で渡す場合があるため float に変換を試みる
        try:
            if lat is not None:
                lat = float(lat)
            if lon is not None:
                lon = float(lon)
        except Exception as e:
            print(f"⚠️ on_location: coordinate parse error: {e} - kwargs={kwargs}")
            return

        if lat and lon:
            print(f"🛰️ map2 on_location: lat={lat:.6f}, lon={lon:.6f} (kwargs keys: {list(kwargs.keys())})")
            if not self.map_center_updated:
                self.mapview.center_on(lat, lon)
                self.map_center_updated = True
            Clock.schedule_once(lambda dt: self._update_my_marker(lat, lon), 0)
        else:
            print(f"⚠️ map2 on_location: no lat/lon in kwargs: {kwargs}")

    def on_status(self, stype, status):
        print(f"GPS status: {stype} - {status}")

    def _start_debug_mode(self):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                user_mail = data[0].get("user_mail")
            else:
                user_mail = data.get("user_mail")
            if user_mail:
                url = f"{SUPABASE_URL}/rest/v1/location?select=location&mail=eq.{user_mail}"
                headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                res = requests.get(url, headers=headers, timeout=6)
                if res.status_code == 200 and res.json():
                    loc_str = res.json()[0].get("location")
                    if loc_str:
                        lat, lon = map(float, loc_str.strip("{}").split(","))
                        self.lat, self.lon = lat, lon
                        self.mapview.center_on(lat, lon)
                        self.map_center_updated = True
                        Clock.schedule_once(lambda dt: self._update_my_marker(lat, lon), 0.5)
                        return
        except Exception as e:
            print(f"debug_mode load last location error: {e}")

        # フォールバック（東京駅付近）
        self.lat, self.lon = 35.681236, 139.767125
        self.mapview.center_on(self.lat, self.lon)
        self.map_center_updated = True
        Clock.schedule_once(lambda dt: self._update_my_marker(self.lat, self.lon), 0.5)

    def _simulate_location(self, dt):
        self.lat += random.uniform(-0.0003, 0.0003)
        self.lon += random.uniform(-0.0003, 0.0003)
        self._update_my_marker(self.lat, self.lon)

    # ---------- マーカー & 送信 ----------
    def _update_my_marker(self, lat, lon, pin_source="img/pin.png"):
        if self.my_marker:
            self.my_marker.lat = lat
            self.my_marker.lon = lon
        else:
            self.my_marker = MapMarker(lat=lat, lon=lon, source=pin_source)
            self.mapview.add_marker(self.my_marker)
        self.lat, self.lon = lat, lon
        print(f"📍 map2 _update_my_marker: marker lat={self.my_marker.lat:.6f}, lon={self.my_marker.lon:.6f}")

    def send_my_location(self, *_):
        if hasattr(self, 'lat') and hasattr(self, 'lon'):
            # users.json からメール取得
            global MY_USER_MAIL
            if not MY_USER_MAIL:
                try:
                    with open("users.json", "r", encoding="utf-8") as f:
                        d = json.load(f)
                    MY_USER_MAIL = d[0].get("user_mail") if isinstance(d, list) and d else None
                except Exception:
                    MY_USER_MAIL = None
            if MY_USER_MAIL:
                print(f"📤 map2 send_my_location: sending lat={self.lat:.6f}, lon={self.lon:.6f} for {MY_USER_MAIL}")
                threading.Thread(
                    target=lambda: save_my_location((self.lat, self.lon)),
                    daemon=True
                ).start()
            else:
                print("⚠️ map2 send_my_location: MY_USER_MAIL not available")

    # ---------- フレンド更新 ----------
    def update_friends(self, *_):
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return
            user_mail = data[0].get("user_mail")
            if not user_mail:
                return

            friends_mail_list = fetch_friends_by_mail(user_mail) or []
            for f_mail in friends_mail_list:
                loc = fetch_friend_location(f_mail)
                if not loc:
                    continue
                lat, lon = loc
                self._update_friend_marker(f_mail, lat, lon)
        except Exception as e:
            print(f"update_friends error: {e}")

    def _update_friend_marker(self, friend_mail, lat, lon):
        if friend_mail in self.friend_markers:
            mk = self.friend_markers[friend_mail]
            mk.lat = lat
            mk.lon = lon
        else:
            # fetch_friend_icon expects a user_id. Convert mail -> user_id first.
            try:
                friend_id = get_user_id_by_mail(friend_mail)
            except Exception as e:
                print(f"⚠️ get_user_id_by_mail error: {e}")
                friend_id = None

            icon_url = None
            if friend_id:
                try:
                    icon_url = fetch_friend_icon(friend_id)
                except Exception as e:
                    print(f"⚠️ fetch_friend_icon error: {e}")

            if not icon_url:
                icon_url = "img/cat_placeholder.png"

            mk = FriendMarker(lat, lon, icon_url, friend_mail, self.app_instance)
            self.mapview.add_marker(mk)
            self.friend_markers[friend_mail] = mk

    # ---------- 初期化 ----------
    def _initialize_user_location_on_open(self):
        global MY_USER_MAIL
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                current_user_json = data[0]
                user_mail = current_user_json.get("user_mail")
                if user_mail:
                    MY_USER_MAIL = user_mail
                    initialize_user_location(user_mail)
        except Exception as e:
            print(f"initialize_user_location_on_open error: {e}")

    # ---------- 戻るボタン ----------
    def _on_back_button(self, window, key, *args):
        if key != 27:
            return False
        # 親アプリに任せる（back_to_map があれば呼ぶ）
        if self.app_instance and hasattr(self.app_instance, 'back_to_map'):
            self.app_instance.back_to_map()
            return True
        return False

    # ---------- 画面離脱で定期処理停止 ----------
    def on_leave(self):
        try:
            if hasattr(self, 'friend_update_event'): self.friend_update_event.cancel()
            if hasattr(self, 'send_location_event'): self.send_location_event.cancel()
            if hasattr(self, 'location_event'): self.location_event.cancel()
            if HAS_GPS:
                try: gps.stop()
                except: pass
            Window.unbind(on_keyboard=self._on_back_button)
        except Exception as e:
            print(f"on_leave cleanup error: {e}")


# ========= 単体テスト起動用 =========
class _TestApp(App):
    def build(self):
        request_location_permissions()
        return MainScreen()

if __name__ == "__main__":
    _TestApp().run()
        self.main_screen = MainScreen2(app_instance=self)  # 変更
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
        self.main_screen = MainScreen2(app_instance=self)
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
        
        from friend_profile import FriendProfileScreen
        self.root.clear_widgets()
        profile_screen = FriendProfileScreen(friend_mail=friend_mail, app_instance=self)
        self.root.add_widget(profile_screen)
    
    def open_specify_location(self):
        """場所を指定する画面を開く"""
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        self.root.clear_widgets()
        specify_screen = SpecifyLocationScreen(app_instance=self)
        self.root.add_widget(specify_screen)
    
    def open_meeting_map(self, friend_mail):
        """待ち合わせ用のマップ画面を開く"""
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        self.root.clear_widgets()
        self.main_screen = MainScreen2(app_instance=self, friend_mail=friend_mail)
        self.root.add_widget(self.main_screen)
        print(f"🗺️ 友人 {friend_mail} との待ち合わせ場所を指定してください")
        
    def open_map3(self, meeting_id):
        """map3画面を開く"""
        # 定期処理を停止
        if hasattr(self, 'main_screen'):
            self.main_screen.stop_updates()
        
        self.root.clear_widgets()
        from map3 import MainScreen as Map3MainScreen
        # map3.pyのMainScreenをそのまま追加（FloatLayout）
        map3_screen = Map3MainScreen(app_instance=self, meeting_id=meeting_id)
        self.root.add_widget(map3_screen)


    

if __name__ == '__main__':
    MyApp().run()
