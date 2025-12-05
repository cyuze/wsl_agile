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
# 丸アイコン（Stencil） - タッチ透過
# ===============================================================
class CircleImageView(StencilView):
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

    # タッチ透過
    def on_touch_down(self, touch): return False
    def on_touch_move(self, touch): return False
    def on_touch_up(self, touch): return False

# ===============================================================
# 友だちマーカー（丸アイコン付き）
# ===============================================================
class FriendMarker(MapLayer):
    def __init__(self, mapview, lat, lon, icon_url, **kwargs):
        super().__init__(**kwargs)
        self.mapview = mapview
        self.lat = lat
        self.lon = lon
        self.size = (70, 70)
        self.icon = CircleImageView(source=icon_url, size=self.size, size_hint=(None, None))
        self.add_widget(self.icon)
        mapview.bind(on_map_relocated=self.update_position, zoom=self.update_position)
        self.update_position()

    # タッチ透過
    def on_touch_down(self, touch): return False
    def on_touch_move(self, touch): return False
    def on_touch_up(self, touch): return False

    def update_position(self, *args):
        try:
            x, y = self.mapview.get_window_xy_from(lat=self.lat, lon=self.lon, zoom=self.mapview.zoom)
            self.icon.pos = (x - self.size[0]/2, y - self.size[1]/2)
        except Exception:
            pass

# ===============================================================
# 背景付き画像ボタン
# ===============================================================
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (1,1,1,1)

        self.friend_meetings = {}
        self.friend_markers = {}
        self.friend_icons = {}
        self.my_marker = None

        # MapView
        self.mapview = MapView(lat=39.701083, lon=141.136132, zoom=14, map_source=GSImapSource())
        self.add_widget(self.mapview)

        # 下部ボタン
        btns = [{'image':'img/friend.png','x':0.2},
                {'image':'img/chat.png','x':0.4},
                {'image':'img/map.png','x':0.6},
                {'image':'img/settings.png','x':0.8}]
        for b in btns:
            btn = ImageButton(image_source=b['image'], size_hint=(None,None), size=(140,140), pos_hint={'center_x':b['x'],'y':0.05})
            btn.bind(on_press=lambda i,name=b['image']: print(f"{name} ボタンが押されました"))
            self.add_widget(btn)

        # GPS
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

        Clock.schedule_interval(self.update_friends, 5)

    # ===========================================================
    # GPS / デバッグ
    # ===========================================================
    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat and lon: self.update_my_marker(lat, lon)
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

    # ===========================================================
    # 自分マーカー更新
    # ===========================================================
    def update_my_marker(self, lat, lon):
        if self.my_marker:
            self.my_marker.lat = lat
            self.my_marker.lon = lon
        else:
            self.my_marker = MapMarker(lat=lat, lon=lon, source="img/pin.png")
            self.mapview.add_marker(self.my_marker)

    # ===========================================================
    # 友だち情報更新
    # ===========================================================
    def update_friends(self, dt):
        friends = self.fetch_friends(MY_ID)
        for fid in friends:
            if fid not in self.friend_meetings:
                mid = self.fetch_or_create_meeting(MY_ID, fid)
                if mid: self.friend_meetings[fid] = mid
            self.fetch_friend_location(fid)

    def fetch_friends(self, user_id):
        url = f"{SUPABASE_URL}/rest/v1/friend"
        params = {"select":"send_user,recive_user,permission",
                  "or":f"(send_user.eq.{user_id},recive_user.eq.{user_id})"}
        headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
        try:
            res = requests.get(url,headers=headers,params=params)
            if res.status_code!=200: return []
            friends = []
            for r in res.json():
                if not r.get("permission"): continue
                fid = r["recive_user"] if r["send_user"]==user_id else r["send_user"]
                if fid!=user_id: friends.append(fid)
            return friends
        except Exception as e:
            print("⚠️ fetch_friends:", e)
            return []

    def fetch_or_create_meeting(self, a, b):
        url = f"{SUPABASE_URL}/rest/v1/meeting"
        params = {"select":"meeting_id",
                  "or":f"(and(userA_id.eq.{a},userB_id.eq.{b}),and(userA_id.eq.{b},userB_id.eq.{a}))"}
        headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
        try:
            res = requests.get(url,headers=headers,params=params)
            data = res.json()
            if data: return data[0]["meeting_id"]
            payload = {"userA_id":a,"userB_id":b}
            headers["Content-Type"]="application/json"
            res = requests.post(url,headers=headers,data=json.dumps(payload))
            if res.status_code in (200,201): return res.json()[0]["meeting_id"]
        except Exception as e:
            print("⚠️ fetch_or_create_meeting:", e)
        return None

    def fetch_friend_icon(self, friend_id):
        if friend_id in self.friend_icons: return self.friend_icons[friend_id]
        url = f"{SUPABASE_URL}/rest/v1/users?select=icon_url&user_id=eq.{friend_id}"
        headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
        try:
            res = requests.get(url,headers=headers)
            data = res.json()
            if data:
                self.friend_icons[friend_id] = data[0]["icon_url"]
                return data[0]["icon_url"]
        except Exception as e:
            print("⚠️ fetch_friend_icon:", e)
        return None

    def fetch_friend_location(self, friend_id):
        mid = self.friend_meetings.get(friend_id)
        if not mid: return
        url = f"{SUPABASE_URL}/rest/v1/meeting?select=userB_zahyo,userA_zahyo,userA_id,userB_id&meeting_id=eq.{mid}"
        headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
        try:
            res = requests.get(url,headers=headers)
            if res.status_code!=200: return
            data = res.json()
            if not data: return
            row = data[0]
            raw = row["userB_zahyo"] if row["userA_id"]==MY_ID else row["userA_zahyo"]
            if not raw: return
            lat, lon = map(float, raw.split(","))
            self.update_friend_marker(friend_id, lat, lon)
        except Exception as e:
            print("⚠️ fetch_friend_location:", e)

    def update_friend_marker(self, friend_id, lat, lon):
        if friend_id in self.friend_markers:
            marker = self.friend_markers[friend_id]
            marker.lat = lat
            marker.lon = lon
            marker.update_position()
        else:
            icon_url = self.fetch_friend_icon(friend_id) or "img/default_user.png"
            marker = FriendMarker(self.mapview, lat, lon, icon_url)
            self.mapview.add_layer(marker)
            self.friend_markers[friend_id] = marker

# ===============================================================
# アプリ本体
# ===============================================================
class MyApp(App):
    def build(self):
        request_location_permissions()
        return MainScreen()

if __name__ == '__main__':
    MyApp().run()
