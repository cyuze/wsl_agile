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
from kivy.metrics import dp
from kivy.utils import get_color_from_hex

from map3_service import (
    MainScreenLogic,
    request_location_permissions,
    get_active_meeting_info
)
from map_service import fetch_friend_location, fetch_friend_icon, get_user_id_by_mail

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
# 小さいピンマーカー
# ========================
class SmallPinMarker(MapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(45), dp(45))


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
        self.size = (dp(56), dp(56))
        self.friend_mail = friend_mail
        self.app_instance = app_instance

        with self.canvas.before:
            # 外枠（薄い緑）
            Color(*get_color_from_hex('#D1EFC7'))
            self.outer = Ellipse(
                size=(self.size[0] + dp(8), self.size[1] + dp(8)),
                pos=(self.pos[0] - dp(4), self.pos[1] - dp(4))
            )
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
        self.outer.pos = (self.pos[0] - dp(4), self.pos[1] - dp(4))
        self.outer.size = (self.size[0] + dp(8), self.size[1] + dp(8))



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
        self.meeting_marker = None
        self.my_marker = None
        self.friend_markers = []

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
        self.meeting_bar = FloatLayout(size_hint=(1, None), height=dp(170), pos_hint={'top': 1})

        with self.meeting_bar.canvas.before:
            Color(1, 1, 1, 0.9)
            self.meeting_bg = RoundedRectangle(size=self.meeting_bar.size, pos=self.meeting_bar.pos, radius=[20])
        self.meeting_bar.bind(size=self._update_meeting_bg, pos=self._update_meeting_bg)

        self.meeting_status_label = Label(
            text="待ち合わせ中",
            size_hint=(None, None),
            size=(300, 40),
            pos_hint={'x': 0.05, 'center_y': 0.75},
            color=(0, 0, 0, 1),
            font_size=50,
            halign="left",
            font_name="NotoSansJP"
        )

        # self.meeting_friend_label = Label(
        #     text="相手: 読み込み中…",
        #     size_hint=(None, None),
        #     size=(600, 30),
        #     pos_hint={'x': 0, 'center_y': 0.4},
        #     color=(0.2, 0.2, 0.2, 1),
        #     font_size=45,
        #     font_name="NotoSansJP"
        #     halign="left",
        #     valign="middle"
        # )
        self.meeting_friend_label = Label(
            text="相手: 読み込み中…",
            size_hint=(1, None),
            height=dp(30),
            pos_hint={'x': 0.03, 'center_y': 0.4},
            color=(0.2, 0.2, 0.2, 1),
            font_size=39,
            font_name="NotoSansJP",
            halign="left",
            valign="middle"
        )

        self.meeting_place_label = Label(
            text="場所: 読み込み中…",
            size_hint=(1, None),
            height=dp(30),
            pos_hint={'x': 0.03, 'center_y': 0.15},
            color=(0.2, 0.2, 0.2, 1),
            font_size=39,
            font_name="NotoSansJP",
            halign="left",
            valign="middle"
        )

        # self.meeting_place_label = Label(
        #     text="場所: 読み込み中…",
        #     size_hint=(None, None),
        #     size=(600, 30),
        #     pos_hint={'x': 0, 'center_y': 0.15},
        #     color=(0.2, 0.2, 0.2, 1),
        #     font_size=45,
        #     font_name="NotoSansJP"
        # )

        self.end_button = Button(
            text="終了",
            size_hint=(None, None),
            size=(160, 80),
            pos_hint={'right': 0.97, 'center_y': 0.5},
            background_normal="",
            background_color=(0.671, 0.905, 0.510, 1),
            color=(0, 0, 0, 1),
            font_size=50,
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
        # 定期的に会議ステータスをチェック（相手が終了したら自動で戻る）
        # -------------------------
        self.meeting_status_check_event = Clock.schedule_interval(self.check_meeting_status, 5)

    # -------------------------
    # meeting 情報読み込み
    # -------------------------
    def load_meeting_info(self):
        try:
            import json  # ← 追加
            with open("users.json", "r", encoding="utf-8") as f:
                data = f.read()
            user = json.loads(data)[0]
            my_mail = user.get("user_mail")

            info = get_active_meeting_info(my_mail)
            if info:
                lat, lon = info["location"]
                place_name = info["place_name"]
                members = info["members"]
                self.meeting_id = info["meeting_id"]

                # マップの中心を待ち合わせ地点に移動
                self.mapview.center_on(lat, lon)
                
                # 待ち合わせ地点にマーカーを追加
                if self.meeting_marker:
                    self.mapview.remove_marker(self.meeting_marker)
                self.meeting_marker = SmallPinMarker(lat=lat, lon=lon, source="img/red_pin.png")
                self.mapview.add_marker(self.meeting_marker)
                print(f"📍 待ち合わせ地点マーカーを追加: ({lat}, {lon})")
                
                # 場所名を表示
                if place_name:
                    self.meeting_place_label.text = f"場所: {place_name}"
                else:
                    self.meeting_place_label.text = f"場所: 緯度 {lat:.6f}, 経度 {lon:.6f}"

                # 相手のメールアドレスを表示
                others = [m for m in members if m != my_mail]
                if others:
                    self.meeting_friend_label.text = f"相手: {', '.join(others)}"
                else:
                    self.meeting_friend_label.text = "相手: なし"

                # 自分と相手の現在地マーカーを追加
                self._add_member_markers(my_mail, others)
                
                print(f"✅ 待ち合わせ情報を描画しました")
                print(f"   - meeting_id: {self.meeting_id}")
                print(f"   - 場所: {place_name}")
                print(f"   - 座標: ({lat}, {lon})")
                print(f"   - メンバー: {members}")

        except Exception as e:
            print(f"⚠️ load_meeting_info error: {e}")
            import traceback
            traceback.print_exc()

    # -------------------------
    # 会議ステータスチェック（定期実行）
    # -------------------------
    def check_meeting_status(self, dt):
        """定期的に会議のステータスをチェックし、終了していたらmap画面に戻る"""
        try:
            if not self.meeting_id:
                return
            
            import json
            import requests
            
            # Supabase設定
            SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
            SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"
            
            # meeting_sharesテーブルでこのmeeting_idのstatusがtrueのレコードがあるかチェック
            url = f"{SUPABASE_URL}/rest/v1/meeting_shares"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            params = {
                "select": "id,status",
                "meeting_id": f"eq.{self.meeting_id}",
                "status": "eq.true"
            }
            
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                # statusがtrueのレコードがなければ、会議は終了している
                if not data or len(data) == 0:
                    print("⚠️ 会議が終了しました - map画面に自動で戻ります")
                    # 定期チェックを停止
                    if hasattr(self, 'meeting_status_check_event'):
                        self.meeting_status_check_event.cancel()
                    
                    # map画面に戻る
                    if self.app_instance:
                        Clock.schedule_once(lambda dt: self._return_to_map(), 0)
        
        except FileNotFoundError:
            pass  # users.jsonがない場合は何もしない
        except Exception as e:
            print(f"⚠️ check_meeting_status error: {e}")
    
    def _return_to_map(self):
        """map画面に戻る処理"""
        # meeting_status_check_eventをキャンセル（重要：2回目以降の自動化に必須）
        if hasattr(self, 'meeting_status_check_event') and self.meeting_status_check_event:
            self.meeting_status_check_event.cancel()
            print("✅ check_meeting_status イベントをキャンセルしました")
        
        if self.app_instance:
            from kivy.uix.screenmanager import ScreenManager
            if isinstance(self.app_instance.root, ScreenManager):
                # mapスクリーンが存在するか確認
                if self.app_instance.root.has_screen("map"):
                    # mapスクリーンの定期処理を再開（重要：2回目以降の自動化に必須）
                    if hasattr(self.app_instance, 'main_screen') and hasattr(self.app_instance.main_screen, 'resume_updates'):
                        self.app_instance.main_screen.resume_updates()
                        print("📍 map.pyの定期処理を再開しました")
                    self.app_instance.root.current = "map"
                else:
                    # mapスクリーンがない場合は作成
                    from kivy.uix.screenmanager import Screen
                    from map import MainScreen as MapMainScreen
                    
                    class MapScreen(Screen):
                        def __init__(self, app_inst, **kwargs):
                            super().__init__(name="map", **kwargs)
                            app_inst.main_screen = MapMainScreen(
                                app_instance=app_inst, 
                                current_user=app_inst.current_user
                            )
                            self.add_widget(app_inst.main_screen)
                    
                    map_screen = MapScreen(app_inst=self.app_instance)
                    self.app_instance.root.add_widget(map_screen)
                    self.app_instance.root.current = "map"
            else:
                self.app_instance.back_to_map()
    
    # -------------------------
    # 上部バー背景更新
    # -------------------------
    def _update_meeting_bg(self, *args):
        self.meeting_bg.size = self.meeting_bar.size
        self.meeting_bg.pos = self.meeting_bar.pos
        width = self.meeting_bar.width * 0.9  # 左右に余白を作る
        self.meeting_friend_label.text_size = (width, None)
        self.meeting_place_label.text_size = (width, None)


    # -------------------------
    # 自分・相手のマーカー追加
    # -------------------------
    def _add_member_markers(self, my_mail, others):
        try:
            if self.my_marker:
                self.mapview.remove_marker(self.my_marker)
                self.my_marker = None
            for marker in self.friend_markers:
                self.mapview.remove_marker(marker)
            self.friend_markers = []

            my_loc = fetch_friend_location(my_mail)
            if my_loc:
                my_lat, my_lon = my_loc
                self.my_marker = MapMarker(lat=my_lat, lon=my_lon, source="img/pin.png")
                self.mapview.add_marker(self.my_marker)
                print(f"🙋 自分マーカーを追加: ({my_lat}, {my_lon})")

            for friend_mail in others:
                friend_loc = fetch_friend_location(friend_mail)
                if friend_loc:
                    f_lat, f_lon = friend_loc
                    icon_url = None
                    try:
                        friend_id = get_user_id_by_mail(friend_mail)
                    except Exception as e:
                        print(f"⚠️ get_user_id_by_mail error: {e}")
                        friend_id = None

                    if friend_id:
                        try:
                            icon_url = fetch_friend_icon(friend_id)
                        except Exception as e:
                            print(f"⚠️ fetch_friend_icon error: {e}")

                    if not icon_url:
                        icon_url = "img/cat_placeholder.png"

                    marker = FriendMarker(f_lat, f_lon, icon_url, friend_mail, self.app_instance)
                    self.mapview.add_marker(marker)
                    self.friend_markers.append(marker)
                    print(f"👥 相手マーカーを追加: {friend_mail} ({f_lat}, {f_lon})")
        except Exception as e:
            print(f"⚠️ _add_member_markers error: {e}")


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