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
from kivy.uix.widget import Widget
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, RoundedRectangle
from kivy.metrics import dp, sp
import requests
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from picture import PictureScreen



SUPABASE_URL = 'https://impklpvfmyvydnoayhfj.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4'

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def get_user(user_name: str):
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {"select": "user_id,user_name,icon_url", "user_name": f"eq.{user_name}"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Supabase error {res.status_code}: {res.text}")
    data = res.json()
    if not data:
        return None
    return data[0]

row = get_user("yuze")
if row is None:
    raise Exception("ユーザーが見つかりませんでした。")

user_name = row["user_name"]
img_url = row["icon_url"]

LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236 / 255, 244 / 255, 232 / 255, 1)

# === スケーリング関数 ===
scale = Window.dpi / 160.0   # 160dpiを基準に拡大
def Sdp(value): return dp(value * scale)
def Ssp(value): return sp(value * scale)

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
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(rgba=(0.671, 0.906, 0.510, 1))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(12)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# 設定画面
# class SettingsScreen(BoxLayout, Screen):
class SettingsScreen(Screen):
    def __init__(self, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.current_user = {"user_name": "yuze"}  # ← 本来はログイン時にセット
        
        Window.clearcolor = (236 / 255, 244 / 255, 232 / 255, 1)

        self.app_instance = app_instance

        # 全体を縦に並べるレイアウト
        main_layout = BoxLayout(orientation="vertical")

        def left_label(text, **kw):
            lbl = Label(
                text=text,
                font_name="Japanese",
                halign="left",
                valign="middle",
                color=(0, 0, 0, 1),
                size_hint_y=None,
                font_size=Ssp(28),
                height=Sdp(40),
                **kw
            )
            lbl.bind(size=lambda s, _: setattr(s, "text_size", s.size))
            return lbl
        
        def header_label(text, **kw):
            hlbl = Label(
                text=text,
                font_name="Japanese",
                halign="center",
                valign="middle",
                color=(0, 0, 0, 1),
                size_hint_y=None,
                font_size=Ssp(40),
                height=Sdp(80),
                **kw
            )
            hlbl.bind(size=lambda s, _: setattr(s, "text_size", s.size))
            return hlbl

        # === 固定ヘッダー部分 ===
        header = header_label("設定")
        main_layout.add_widget(header)

        # === スクロール部分 ===
        scroll = ScrollView(size_hint=(1, 1))

        root_layout = BoxLayout(
            orientation="vertical",
            padding=[Sdp(30), Sdp(20), Sdp(30), Sdp(20)],
            spacing=Sdp(50),
            size_hint_y=None
        )
        root_layout.bind(minimum_height=root_layout.setter("height"))

        # 以下はスクロール対象の要素
        root_layout.add_widget(left_label("アカウント編集"))

        # プロフィール
        profile_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(100),
            size_hint_y=None,
            height=Sdp(160)
        )
        profile_layout.add_widget(Widget(size_hint_x=0.3))
        self.profile_icon = CircleImageView(
            source=img_url,
            size_hint=(None, None),
            size=(Sdp(120), Sdp(120))
        )
        profile_layout.add_widget(self.profile_icon)
        name_label = Label(
            text=user_name,
            font_size=Ssp(32),
            color=(0, 0, 0, 1),
            font_name="Japanese",
            size_hint=(None, None),
            height=Sdp(80)
        )
        profile_layout.add_widget(name_label)
        profile_layout.add_widget(Widget(size_hint_x=1))
        root_layout.add_widget(profile_layout)


        # 編集ボタン
        edit_layout = AnchorLayout(
            anchor_x="center",
            anchor_y="bottom",
            size_hint_y=None,
            height=Sdp(80)
        )
        inner_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(60),
            size_hint=(None, None),
            width=Sdp(360),
            height=Sdp(80)
        )
        edit_button1 = RoundedButton(
            text="編集",
            size_hint=(None, None),
            color=(0, 0, 0, 1),
            size=(Sdp(140), Sdp(70)),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_imgEdit_press
        )
        edit_button2 = RoundedButton(
            text="編集",
            size_hint=(None, None),
            color=(0, 0, 0, 1),
            size=(Sdp(140), Sdp(70)),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_nameEdit_press
        )
        inner_layout.add_widget(edit_button1)
        inner_layout.add_widget(edit_button2)
        edit_layout.add_widget(inner_layout)
        root_layout.add_widget(edit_layout)

        # 通知
        root_layout.add_widget(left_label("通知"))
        notif_layout = GridLayout(
            cols=2,
            spacing=Sdp(20),
            size_hint_y=None,
            height=Sdp(160)
        )
        notif_layout.add_widget(left_label("位置情報関係"))
        notif_layout.add_widget(Switch(active=True))
        notif_layout.add_widget(left_label("待ち合わせ時間"))
        notif_layout.add_widget(Switch(active=False))
        root_layout.add_widget(notif_layout)

        # プライバシー
        root_layout.add_widget(left_label("プライバシー"))
        privacy_layout = GridLayout(
            cols=2,
            spacing=Sdp(20),
            size_hint_y=None,
            height=Sdp(80)
        )
        privacy_layout.add_widget(left_label("位置情報の表示"))
        privacy_layout.add_widget(Switch(active=True))
        root_layout.add_widget(privacy_layout)
        
        # 確定
        root_layout.add_widget(RoundedButton(
            text="確定",
            color=(0,0,0,1),
            size_hint_y=None,
            height=Sdp(70),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_submit_press
        ))
        root_layout.add_widget(RoundedButton(
            text="ログアウト",
            color=(0,0,0,1),
            size_hint_y=None,
            height=Sdp(70),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_logout_press
        ))

        # ScrollView にスクロール対象を追加
        scroll.add_widget(root_layout)

        # main_layout に ScrollView を追加
        main_layout.add_widget(scroll)

        # Screen に追加
        self.add_widget(main_layout)


    # イベントハンドラ
    def on_imgEdit_press(self, instance):
        print("画像編集ボタンが押されました。編集画面に遷移します。")
        if self.app_instance:
            self.app_instance.open_picture(caller="settings")


    def on_nameEdit_press(self, instance):
        print("名前編集ボタンが押されました。編集画面に遷移します。")

    def on_logout_press(self, instance):
        print("ログアウトボタンが押されました。ログイン画面に遷移します。")
        self.manager.current = "friend_profile"
        
    def on_submit_press(self, instance):
        print("確定ボタンが押されました。変更内容を確定します。")
        
    def update_icon_image(self, image_path):
        """設定画面のアイコン画像を更新"""
        if self.profile_icon:
            self.profile_icon.source = image_path
            # AsyncImage を直接更新
            self.profile_icon.img.source = image_path
            self.profile_icon.img.reload()


    def update_user_icon(self, icon_path):
        """ログイン中ユーザーのアイコンを更新"""
        try:
            user_name = self.current_user["user_name"]

            # ファイル名を決定
            safe_name = user_name.replace('@', '_at_').replace('.', '_')
            file_name = f"{safe_name}_icon.png"

            # 画像ファイル読み込み
            with open(icon_path, "rb") as f:
                image_data = f.read()

            # Storage にアップロード（上書き）
            storage_url = f"{SUPABASE_URL}/storage/v1/object/icon/{file_name}"
            storage_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/png",
                "x-upsert": "true"
            }
            res = requests.post(storage_url, headers=storage_headers, data=image_data)

            if res.status_code not in [200, 201]:
                print("Storage error:", res.text)
                return False

            # 公開 URL
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/icon/{file_name}"

            # users テーブルを UPDATE
            db_url = f"{SUPABASE_URL}/rest/v1/users"
            params = {"user_name": f"eq.{user_name}"}
            payload = {"icon_url": public_url}
            res = requests.patch(db_url, headers=headers, params=params, json=payload)

            if res.status_code == 200:
                print("アイコン更新成功")
                return True
            else:
                print("DB error:", res.text)
                return False

        except Exception as e:
            print("更新失敗:", e)
            return False
        
    def on_enter(self):
        """この画面が表示される時にキーボードイベントをバインド"""
        Window.bind(on_keyboard=self.on_back_button)

    def on_leave(self):
        """この画面が離れる時にキーボードイベントをアンバインド"""
        try:
            Window.unbind(on_keyboard=self.on_back_button)
        except:
            pass

    def on_back_button(self, window, key, *args):
        if key == 27:
                self.app_instance.back_to_map()
                return True
        return False



class SettingsApp(App):
    def build(self):
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(PictureScreen(name="picture"))
        # ここで friend_request 画面も追加しておくと戻る遷移が動作する
        # self.sm.add_widget(FriendRequestScreen(name="friend_request"))

        self.sm.current = "settings"  # 起動時は設定画面

        


if __name__ == "__main__":
    SettingsApp().run()