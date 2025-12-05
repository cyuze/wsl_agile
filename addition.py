from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.metrics import dp, sp
import requests

LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")

# ✅ Supabase接続
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# ✅ レスポンシブ対応のテキスト入力
class LayeredTextInput(FloatLayout):
    def __init__(self, parent_app, **kwargs):
        super().__init__(**kwargs)
        self.parent_app = parent_app

        with self.canvas:
            Color(rgba=(0.9, 0.9, 0.9, 1))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

        self.text_input = TextInput(
            hint_text="友人のIDを入力または検索",
            font_name="Japanese",
            font_size=sp(14),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            hint_text_color=(0.4, 0.4, 0.4, 1),
            background_normal='',
            background_active='',
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            padding=[dp(12), dp(12)],
            multiline=False,
            input_type='text',
        )
        self.text_input.bind(text=self.on_text_change)
        self.add_widget(self.text_input)

        self.bind(pos=self.update_bg, size=self.update_bg)

    def on_text_change(self, instance, value):
        if self.parent_app.search_scheduled:
            self.parent_app.search_scheduled.cancel()
        self.parent_app.search_scheduled = Clock.schedule_once(
            lambda dt: self.parent_app.search_user(), 0.5
        )

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = [dp(12)]


# ✅ レスポンシブ対応のタイトルラベル
class OverlappingLabel(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.update_size()

        with self.canvas.before:
            Color(rgba=get_color_from_hex('#ABE782'))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

        self.label = Label(
            text="フレンド承認",
            font_name="Japanese",
            font_size=sp(18),
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=self.size,
            halign='left',
            valign='middle',
            padding=(dp(15), 0)
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)

        self.bind(pos=self.update_bg, size=self.update_bg)
        Window.bind(size=self.on_window_resize)

    def update_size(self):
        width = Window.width
        if width < dp(360):
            self.size = (dp(130), dp(36))
        elif width < dp(400):
            self.size = (dp(140), dp(38))
        else:
            self.size = (dp(150), dp(40))

    def on_window_resize(self, *args):
        self.update_size()
        self.label.size = self.size
        self.label.text_size = self.size

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = [dp(12)]
        self.label.pos = self.pos


# ✅ レスポンシブ対応のユーザー情報行
class UserInfoRow(BoxLayout):
    def __init__(self, parent_app, **kwargs):
        kwargs.pop('size_hint', None)
        
        super().__init__(
            orientation='horizontal',
            size_hint=(1, None),
            padding=[dp(12), dp(8)],
            spacing=dp(8),
            **kwargs
        )
        
        self.parent_app = parent_app
        self.update_height()

        with self.canvas.before:
            Color(rgba=get_color_from_hex('#CBF3BB'))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self.update_bg, size=self.update_bg)

        label_box = BoxLayout(orientation='horizontal', size_hint_x=0.65, spacing=dp(4))
        
        self.prefix_label = Label(
            text="ユーザー名：",
            font_name="Japanese",
            font_size=sp(14),
            color=(0, 0, 0, 1),
            size_hint_x=None,
            width=dp(90),
            halign="left",
            valign="middle"
        )
        self.prefix_label.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        
        self.name_label = Label(
            text="",
            font_name="Japanese",
            font_size=sp(14),
            color=(0, 0, 0, 1),
            halign="center",
            valign="middle"
        )
        self.name_label.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        
        label_box.add_widget(self.prefix_label)
        label_box.add_widget(self.name_label)
        self.add_widget(label_box)

        self.send_btn = Button(
            text="送信",
            font_name="Japanese",
            font_size=sp(15),
            size_hint=(None, None),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        self.update_button_size()

        with self.send_btn.canvas.before:
            self.bg_color = Color(rgba=get_color_from_hex('#ABE782'))
            self.btn_rect = RoundedRectangle(pos=self.send_btn.pos, size=self.send_btn.size, radius=[dp(10)])

        def update_rect(instance, value):
            self.btn_rect.pos = instance.pos
            self.btn_rect.size = instance.size
            self.btn_rect.radius = [dp(10)]

        self.send_btn.bind(pos=update_rect, size=update_rect)

        def on_press(instance):
            self.bg_color.rgba = get_color_from_hex('#9DCB6E')

        def on_release(instance):
            self.bg_color.rgba = get_color_from_hex('#ABE782')
            self.parent_app.send_request(instance)

        self.send_btn.bind(on_press=on_press, on_release=on_release)
        self.add_widget(self.send_btn)
        
        Window.bind(size=self.on_window_resize)

    def update_height(self):
        width = Window.width
        if width < dp(360):
            self.height = dp(46)
        else:
            self.height = dp(50)

    def update_button_size(self):
        width = Window.width
        if width < dp(360):
            self.send_btn.size = (dp(65), dp(32))
        elif width < dp(400):
            self.send_btn.size = (dp(70), dp(34))
        else:
            self.send_btn.size = (dp(80), dp(36))

    def on_window_resize(self, *args):
        self.update_height()
        self.update_button_size()

    def set_username(self, username):
        self.name_label.text = username

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = [dp(8)]


# ✅ Kivy UIとロジック
class FriendApp(BoxLayout):
    def __init__(self, user_id=None, **kwargs):
        super().__init__(orientation='vertical', spacing=0, **kwargs)
        self.user_id = user_id  # ログインユーザーのID
        self.search_scheduled = None
        Window.bind(size=self.update_layout)
        self.update_layout()

    def get_content_width(self):
        width = Window.width
        if width < dp(360):
            return width * 0.92
        elif width < dp(400):
            return width * 0.9
        else:
            return min(width * 0.88, dp(500))

    def get_spacing(self):
        width = Window.width
        if width < dp(360):
            return dp(12)
        elif width < dp(400):
            return dp(15)
        else:
            return dp(20)

    def update_layout(self, *args):
        self.clear_widgets()
        
        content_width = self.get_content_width()
        spacing = self.get_spacing()
        
        self.add_widget(Widget(size_hint_y=None, height=spacing))

        self.id_input = LayeredTextInput(self, size_hint=(None, None), width=content_width, height=dp(48))
        self.id_input.pos_hint = {'center_x': 0.5}
        self.add_widget(self.id_input)

        self.add_widget(Widget(size_hint_y=None, height=spacing))

        overlap_container = FloatLayout(size_hint=(None, None), width=content_width, height=dp(68))
        overlap_container.pos_hint = {'center_x': 0.5}

        self.user_info = UserInfoRow(self, width=content_width)
        self.user_info.pos_hint = {'center_x': 0.5, 'y': -0.5}
        overlap_container.add_widget(self.user_info)

        self.title_label = OverlappingLabel()
        self.title_label.pos_hint = {'x': 0, 'top': 1}
        overlap_container.add_widget(self.title_label)

        self.add_widget(overlap_container)
        self.add_widget(Widget(size_hint_y=1))

    def search_user(self):
        user_id = self.id_input.text_input.text.strip()

        if not user_id:
            self.user_info.set_username("")
            return

        try:
            url = f"{SUPABASE_URL}/rest/v1/users"
            params = {"select": "user_name", "user_id": f"eq.{user_id}"}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            
            if res.status_code == 200:
                result = res.json()
                if result and len(result) > 0:
                    username = result[0].get("user_name", "")
                    self.user_info.set_username(username)
                else:
                    self.user_info.set_username("ユーザーが見つかりません")
            else:
                self.user_info.set_username("検索エラー")
        except requests.exceptions.Timeout:
            self.user_info.set_username("タイムアウト")
        except Exception as e:
            print(f"検索エラー: {e}")
            self.user_info.set_username("エラー")

    def send_request(self, instance):
        friend_id = self.id_input.text_input.text.strip()
        
        my_id = "dummy_user_id"
        
        if not friend_id:
            self.show_popup("IDを入力してください")
            return
            
        try:
            url = f"{SUPABASE_URL}/rest/v1/friend"
            data = {
                "send_user": my_id,
                "recive_user": friend_id,
                "permission": False
            }
            res = requests.post(url, headers=headers, json=data, timeout=10)
            
            if res.status_code in [200, 201]:
                self.show_popup("申請を送信しました")
                self.id_input.text_input.text = ""
                self.user_info.set_username("")
            else:
                self.show_popup(f"送信エラー: {res.status_code}")
        except requests.exceptions.Timeout:
            self.show_popup("タイムアウトしました")
        except Exception as e:
            print(f"送信エラー: {e}")
            self.show_popup("送信に失敗しました")

    def show_popup(self, message):
        width = Window.width
        popup_width = min(width * 0.8, dp(300))
        
        popup = Popup(
            title='',
            content=Label(text=message, font_name="Japanese", font_size=sp(14)),
            size_hint=(None, None),
            size=(popup_width, dp(180))
        )
        popup.open()


class FriendAppMain(App):
    def build(self):

        
        Window.clearcolor = get_color_from_hex("#ECF4E8")

        root = AnchorLayout(anchor_x='center', anchor_y='top')
        app_layout = FriendApp(size_hint=(1, 1))
        root.add_widget(app_layout)
        return root


if __name__ == "__main__":
    FriendAppMain().run()