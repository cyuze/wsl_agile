from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.switch import Switch
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, RoundedRectangle, Rectangle
from kivy.metrics import dp, sp
import requests
from kivy.uix.screenmanager import ScreenManager, Screen


SUPABASE_URL = 'https://impklpvfmyvydnoayhfj.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4'

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}
YUZE_ID = "249b83b2-8e94-41d9-9d07-c6d62d47e0bf"

def get_received_requests(user_id):
    url = f"{SUPABASE_URL}/rest/v1/friend"
    params = {
        "select": "send_user,friend_id",
        "recive_user": f"eq.{user_id}",   # yuzeが受け取った申請
        "permission": "eq.false"          # 未承認のみ
    }
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Supabase Error {res.status_code}: {res.text}")
    return res.json()

def get_user_info(user_id):
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {
        "select": "user_name,icon_url",
        "user_id": f"eq.{user_id}"
    }
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Supabase Error {res.status_code}: {res.text}")
    return res.json()[0]

# 🔽 yuzeに届いた申請者の情報をまとめる
pending = get_received_requests(YUZE_ID)

data = []
for req in pending:
    sender_id = req["send_user"]   # 申請者のID
    sender_info = get_user_info(sender_id)
    data.append({
        "user_name": sender_info["user_name"],
        "icon_url": sender_info["icon_url"]
    })
    
LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236/255, 244/255, 232/255, 1)

# === DPIスケーリング ===
scale = Window.dpi / 160.0
def Sdp(value): return dp(value * scale)
def Ssp(value): return sp(value * scale)

# 丸画像
class CircleImageView(StencilView):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        self.img = AsyncImage(source=self.source, allow_stretch=True, keep_ratio=False,
                                size_hint=(None, None), size=self.size)
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
        bg_color = kwargs.pop("background_color", (0.671, 0.906, 0.510, 1))
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            self.bg_color_instruction = Color(rgba=bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(12)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# FriendItem（1行）
class FriendItem(BoxLayout):
    def __init__(self, name, img_src, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = Sdp(140)
        self.padding = (Sdp(15), Sdp(20))
        self.spacing = Sdp(20)

        icon = CircleImageView(source=img_src, size_hint=(None, None), size=(Sdp(100), Sdp(100)))

        name_label = Label(
            text=name,
            font_name="Japanese",
            font_size=Ssp(28),
            halign="left",
            valign="middle",
            size_hint_x=1,
            color=(0,0,0,1),
        )
        name_label.bind(size=name_label.setter("text_size"))

        add_btn = RoundedButton(
            text="追加",
            font_name="Japanese",
            size_hint=(None, None),
            size=(Sdp(100), Sdp(50)),
            font_size=Ssp(22),
            color=(0,0,0,1),
        )
        del_btn = RoundedButton(
            text="削除",
            font_name="Japanese",
            size_hint=(None, None),
            size=(Sdp(100), Sdp(50)),
            font_size=Ssp(22),
            color=(0,0,0,1),
            background_color=(0.537, 0.721, 0.82, 1),
        )

        self.add_widget(icon)
        self.add_widget(name_label)
        self.add_widget(add_btn)
        self.add_widget(del_btn)

        with self.canvas.after:
            Color(0.8, 0.8, 0.8, 1)
            self.border = Rectangle(size=(0, 1), pos=(0, 0))
        self.bind(pos=self.update_border, size=self.update_border)

    def update_border(self, *args):
        vertical_padding = Sdp(5)
        self.border.pos = (self.x, self.y + vertical_padding)
        self.border.size = (self.width, Sdp(3))

# メイン画面
class FriendRequestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root_layout = BoxLayout(orientation="vertical", spacing=Sdp(20), padding=Sdp(10))

        header = Label(
            text="フレンドリクエスト",
            size_hint=(1, None),
            height=Sdp(80),
            font_size=Ssp(40),
            font_name="Japanese",
            color=(0, 0, 0, 1),
        )
        root_layout.add_widget(header)

        scroll = ScrollView(size_hint=(1, 1))

        list_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=Sdp(20),
            padding=Sdp(20)
        )
        list_layout.bind(minimum_height=list_layout.setter("height"))

        for row in data:
            list_layout.add_widget(FriendItem(row["user_name"], row["icon_url"]))

        scroll.add_widget(list_layout)
        root_layout.add_widget(scroll)
        

        # Screen に追加
        self.add_widget(root_layout)
        

    def on_enter(self):
        """画面表示時にキーボードイベントをバインド"""
        Window.bind(on_keyboard=self.on_back_button)
    
    def on_leave(self):
        """画面離脱時にキーボードイベントをアンバインド"""
        Window.unbind(on_keyboard=self.on_back_button)

    def on_back_button(self, window, key, *args):
        """Androidの戻るボタン処理"""
        # key=27 が ESC / Android 戻るボタン
        if key == 27:
            print(f"Back button pressed. Current screen: {self.manager.current if self.manager else 'No manager'}")
            print(f"Available screens: {[s.name for s in self.manager.screens] if self.manager else 'No manager'}")
            
            if self.manager:
                # friend_add画面が存在するか確認
                if self.manager.has_screen("friend_add"):
                    self.manager.current = "friend_add"
                    return True
                else:
                    print("friend_add screen not found!")
            else:
                print("self.manager is None!")
        return False
    
        
class FriendRequestApp(App):
    def build(self):
        return FriendRequestScreen()

if __name__ == "__main__":
    FriendRequestApp().run()