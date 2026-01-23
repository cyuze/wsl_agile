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
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

import requests


# Supabase =============================================================================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def get_user_by_id(user_id: str):
    """user_id から Supabase users テーブルを検索"""
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {"user_id": f"eq.{user_id}", "select": "*"}
    r = requests.get(url, headers=headers, params=params)

    if r.status_code != 200:
        print("Supabase Error:", r.text)
        return None

    data = r.json()
    return data[0] if data else None


# UI scaling ============================================================================
LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236/255, 244/255, 232/255, 1)

scale = Window.dpi / 120.0

def Sdp(v):
    return dp(v * scale)

def Ssp(v):
    return sp(v * scale)


# UI Parts ==============================================================================
class ImageCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = Sdp(10)
        self.size_hint = (None, None)
        self.size = (Sdp(160), Sdp(160))
        with self.canvas.before:
            Color(0.67, 0.91, 0.51, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(25)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


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
            size_hint=(None, None),
            allow_stretch=True,
            keep_ratio=False,
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


class RoundedButton(Button):
    def __init__(self, **kwargs):
        bg = kwargs.pop("background_color", (0.671, 0.906, 0.510, 1))
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        with self.canvas.before:
            Color(*bg)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sdp(25)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# Profile Screen ==========================================================================
class FriendProfileScreen(Screen):
    def __init__(self, friend_id=None, app_instance=None, **kwargs):
        super().__init__(**kwargs)

        # ← Kivy に渡さず、ここで普通に保持する
        self.friend_id = friend_id
        self.app_instance = app_instance

        # Supabase からユーザー情報取得
        user = get_user_by_id(friend_id)
        if user:
            user_name = user["user_name"]
            img_url = user["icon_url"]
        else:
            user_name = "不明なユーザー"
            img_url = "img/default_user.png"

        # 以下 UI =====================================================================
        root_layout = BoxLayout(
            orientation="vertical",
            spacing=Sdp(30),
            size_hint=(None, None),
            size=(Sdp(420), Sdp(300))
        )

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(root_layout)

        # アイコン + 名前
        profile_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(20),
            size_hint_y=None,
            height=Sdp(180)
        )
        profile_layout.add_widget(Widget(size_hint_x=0.1))

        img_card = ImageCard()
        circle = CircleImageView(
            source=img_url,
            size_hint=(None, None),
            size=(Sdp(140), Sdp(140))
        )
        img_card.add_widget(circle)
        profile_layout.add_widget(img_card)

        name_layout = BoxLayout(orientation="vertical")
        name_label = Label(
            text=user_name,
            font_name="Japanese",
            font_size=Ssp(28),
            color=(0, 0, 0, 1),
            size_hint=(1, None),
            height=Sdp(140)
        )
        name_layout.add_widget(name_label)
        profile_layout.add_widget(name_layout)

        root_layout.add_widget(profile_layout)

        # ボタン行1
        row1 = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(60),
            size_hint_y=None,
            height=Sdp(80)
        )
        chat_button = RoundedButton(
            text="チャット",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.67, 0.90, 0.51, 1),
            on_press=self.on_chat_press
        )
        meet_button = RoundedButton(
            text="待ち合わせする",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.67, 0.90, 0.51, 1),
            on_press=self.on_meeting_press
        )
        row1.add_widget(chat_button)
        row1.add_widget(meet_button)
        root_layout.add_widget(row1)

        # ボタン行2（削除）
        row2 = AnchorLayout(
            anchor_x="left",
            anchor_y="center",
            size_hint_y=None,
            height=Sdp(90)
        )
        del_button = RoundedButton(
            text="削除",
            color=(0, 0, 0, 1),
            font_size=Ssp(22),
            size_hint=(None, None),
            size=(Sdp(180), Sdp(70)),
            font_name="Japanese",
            background_color=(0.60, 0.80, 0.90, 1),
            on_press=self.on_delete_press
        )
        row2.add_widget(del_button)
        root_layout.add_widget(row2)

        # add root
        self.add_widget(anchor)

    # ボタンイベント ======================================================================
    def on_chat_press(self, instance):
        print("チャットを開始（相手ID →", self.friend_id, ")")
        if self.app_instance:
            self.app_instance.open_chat("MY_ID", self.friend_id)

    def on_meeting_press(self, instance):
        print("待ち合わせ開始：", self.friend_id)
        if self.app_instance:
            self.app_instance.open_meeting_map(friend_id=self.friend_id)

    def on_delete_press(self, instance):
        print("友達削除：", self.friend_id)

    def on_parent(self, widget, parent):
        """親がセットされたときに呼ばれる。親スクリーンの manager を取得してバインドする。"""
        # 親（通常は wrap という Screen）が割り当てられたら、その manager を取得
        print(f"[DEBUG] FriendProfile.on_parent parent={parent}")
        if parent:
            mgr = getattr(parent, "manager", None)
            # さらに上の祖先を探索して manager を見つける
            ancestor = parent
            while mgr is None and getattr(ancestor, "parent", None):
                ancestor = ancestor.parent
                mgr = getattr(ancestor, "manager", None)

            if mgr is None:
                # まだ ScreenManager に追加されていない可能性があるため、少し遅延して再チェック
                self._deferred_parent = parent
                Clock.schedule_once(lambda dt: self._deferred_bind(), 0.05)
                return

            self._mgr = mgr
            # 戻る先を常に map に固定
            self.previous_screen = "map"

            # 戻るボタンをバインド
            print(f"[DEBUG] FriendProfile binding on_keyboard, mgr={mgr}")
            Window.bind(on_keyboard=self.on_back_button)
        else:
            # 親が外れたらバインド解除
            try:
                print("[DEBUG] FriendProfile unbinding on_keyboard")
                Window.unbind(on_keyboard=self.on_back_button)
            except Exception:
                pass

    def _deferred_bind(self):
        """遅延バインド: 親が ScreenManager に追加された後に manager を探してバインドする。"""
        parent = getattr(self, "_deferred_parent", None)
        if not parent:
            return
        try:
            mgr = getattr(parent, "manager", None)
            ancestor = parent
            while mgr is None and getattr(ancestor, "parent", None):
                ancestor = ancestor.parent
                mgr = getattr(ancestor, "manager", None)

            self._mgr = mgr
            self.previous_screen = "map"
            print(f"[DEBUG] FriendProfile deferred_bind mgr={mgr}")
            if mgr:
                Window.bind(on_keyboard=self.on_back_button)
        except Exception as e:
            print("[DEBUG] FriendProfile deferred_bind error:", e)

    def on_back_button(self, window, key, *args):
        """Android の戻るボタン処理。
        親スクリーン（または見つかった manager）が現在表示中のとき、previous_screen に戻る。
        """
        # key=27 が ESC / Android 戻るボタン
        print(f"[DEBUG] FriendProfile.on_back_button called: key={key}")
        if key != 27:
            return False

        mgr = getattr(self, "_mgr", None) or getattr(self, "manager", None)
        # 親経由で manager を再取得しておく
        if mgr is None and getattr(self, "parent", None):
            mgr = getattr(self.parent, "manager", None)

        print(f"[DEBUG] FriendProfile on_back_button mgr={mgr}, parent={getattr(self,'parent',None)}")
        if mgr:
            # もし現在表示中のスクリーンがこの FriendProfile を含むスクリーンなら戻る
            current = getattr(mgr, "current", None)
            # 親スクリーン名が存在すればそれを確認、なければこのスクリーンの name を確認
            parent_name = getattr(self.parent, "name", None) if getattr(self, "parent", None) else None
            print(f"[DEBUG] FriendProfile on_back_button current={current}, parent_name={parent_name}, self.name={getattr(self,'name',None)}")
            if (parent_name and current == parent_name) or (getattr(self, "name", None) and current == self.name):
                try:
                    mgr.current = getattr(self, "previous_screen", "account")
                except Exception:
                    mgr.current = "account"
                return True

        return False


class FriendProfileApp(App):
    def build(self):
        return FriendProfileScreen()

if __name__ == "__main__":
    FriendProfileApp().run()
