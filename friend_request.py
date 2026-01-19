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
import json
from kivy.uix.screenmanager import ScreenManager, Screen


SUPABASE_URL = 'https://impklpvfmyvydnoayhfj.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4'

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def load_current_user_mail():
    """users.jsonからログイン中のメールアドレスを取得"""
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data and len(data) > 0:
                user_mail = data[0].get('user_mail')
                print(f"✅ ログイン中のメール: {user_mail}")
                return user_mail
    except Exception as e:
        print(f"❌ load_current_user_mail error: {e}")
    return None


def get_received_requests(user_mail):
    """ログインユーザー宛の未承認申請を取得（user_mailベース）"""
    if not user_mail:
        return []
    
    print(f"🔍 未承認申請を検索中... recive_user={user_mail}")
    
    url = f"{SUPABASE_URL}/rest/v1/friend"
    params = {
        "select": "send_user,friend_id,permission",
        "recive_user": f"eq.{user_mail}",
        "permission": "is.null"  # permissionがnullのもののみ
    }
    
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    
    res = requests.get(url, headers=headers, params=params, timeout=10)
    
    print(f"📡 応答: status={res.status_code}")
    print(f"   Response: {res.text}")
    
    if res.status_code != 200:
        print(f"❌ Supabase friend fetch error {res.status_code}: {res.text}")
        return []
    
    result = res.json()
    print(f"✅ 取得した申請: {result}")
    return result


def get_user_info_by_mail(user_mail):
    """user_mailからユーザー情報を取得"""
    if not user_mail:
        return None
    
    print(f"🔍 ユーザー情報取得中... user_mail={user_mail}")
    
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {
        "select": "user_name,icon_url,user_id",
        "user_mail": f"eq.{user_mail}"
    }
    
    res = requests.get(url, headers=headers, params=params, timeout=10)
    
    print(f"📡 応答: status={res.status_code}")
    print(f"   Response: {res.text}")
    
    if res.status_code != 200:
        print(f"❌ Supabase user fetch error {res.status_code}: {res.text}")
        return None
    
    result = res.json()
    user_info = result[0] if result else None
    print(f"✅ ユーザー情報: {user_info}")
    return user_info

    
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
        bg_color = kwargs.pop("background_color", (0.671, 0.906, 0.510, 1))
        super().__init__(**kwargs)
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
# FriendItem（1行）
class FriendItem(BoxLayout):
    def __init__(self, name, img_src, friend_id, sender_mail, parent_screen, **kwargs):
        super().__init__(**kwargs)
        self.friend_id = friend_id
        self.sender_mail = sender_mail
        self.parent_screen = parent_screen
        
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

        # 追加ボタン
        self.add_btn = RoundedButton(
            text="追加",
            font_name="Japanese",
            size_hint=(None, None),
            size=(Sdp(100), Sdp(50)),
            font_size=Ssp(22),
            color=(0,0,0,1),
        )
        self.add_btn_original_color = (0.671, 0.906, 0.510, 1)
        self.add_btn.bind(on_press=self.on_add_press)
        self.add_btn.bind(on_release=self.on_accept)
        
        # 削除ボタン
        self.del_btn = RoundedButton(
            text="削除",
            font_name="Japanese",
            size_hint=(None, None),
            size=(Sdp(100), Sdp(50)),
            font_size=Ssp(22),
            color=(0,0,0,1),
            background_color=(0.537, 0.721, 0.82, 1),
        )
        self.del_btn_original_color = (0.537, 0.721, 0.82, 1)
        self.del_btn.bind(on_press=self.on_del_press)
        self.del_btn.bind(on_release=self.on_reject)

        self.add_widget(icon)
        self.add_widget(name_label)
        self.add_widget(self.add_btn)
        self.add_widget(self.del_btn)

        with self.canvas.after:
            Color(0.8, 0.8, 0.8, 1)
            self.border = Rectangle(size=(0, 1), pos=(0, 0))
        self.bind(pos=self.update_border, size=self.update_border)

    def update_border(self, *args):
        vertical_padding = Sdp(5)
        self.border.pos = (self.x, self.y + vertical_padding)
        self.border.size = (self.width, Sdp(3))
    
    def on_add_press(self, instance):
        """追加ボタンが押された瞬間（視覚フィードバック）"""
        # 元の色より50%暗くする
        instance.bg_color_instruction.rgba = (0.35, 0.55, 0.25, 1)
        print("🟢 追加ボタン押下（色変更）")
        
        # ボタンを無効化（連打防止）
        self.add_btn.disabled = True
        self.del_btn.disabled = True
    
    def on_del_press(self, instance):
        """削除ボタンが押された瞬間（視覚フィードバック）"""
        # 元の色より50%暗くする
        instance.bg_color_instruction.rgba = (0.27, 0.40, 0.50, 1)
        print("🔵 削除ボタン押下（色変更）")
        
        # ボタンを無効化（連打防止）
        self.add_btn.disabled = True
        self.del_btn.disabled = True
    
    def on_accept(self, instance):
        """承認ボタンが離された時（permission=true）"""
        print(f"✅ 承認処理開始: friend_id={self.friend_id}")
        
        # 即座にUIから削除
        self.parent_screen.list_layout.remove_widget(self)
        print("🗑️ UIから即座に削除しました")
        
        # 空リストチェック
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.check_empty_list(), 0.1)
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friend"
            params = {"friend_id": f"eq.{self.friend_id}"}
            data = {"permission": True}
            
            print(f"   URL: {url}")
            print(f"   Params: {params}")
            print(f"   Data: {data}")
            
            res = requests.patch(url, headers=headers, params=params, json=data, timeout=10)
            
            print(f"📡 承認応答: status={res.status_code}")
            print(f"   Response: {res.text}")
            
            # 200と204を両方成功として扱う
            if res.status_code in [200, 204]:
                print("✅ 承認成功（permission=true）")
            else:
                print(f"❌ 承認失敗: {res.status_code}")
                # 失敗したら元に戻す
                if self.parent_screen and self.parent_screen.list_layout:
                    # 空メッセージを削除してからアイテムを追加
                    for child in self.parent_screen.list_layout.children[:]:
                        if isinstance(child, Label):
                            self.parent_screen.list_layout.remove_widget(child)
                    self.parent_screen.list_layout.add_widget(self)
                    instance.bg_color_instruction.rgba = self.add_btn_original_color
                    self.add_btn.disabled = False
                    self.del_btn.disabled = False
        except Exception as e:
            print(f"❌ 承認エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラー時も元に戻す
            if self.parent_screen and self.parent_screen.list_layout:
                # 空メッセージを削除してからアイテムを追加
                for child in self.parent_screen.list_layout.children[:]:
                    if isinstance(child, Label):
                        self.parent_screen.list_layout.remove_widget(child)
                self.parent_screen.list_layout.add_widget(self)
                instance.bg_color_instruction.rgba = self.add_btn_original_color
                self.add_btn.disabled = False
                self.del_btn.disabled = False

    def on_reject(self, instance):
        """拒否ボタンが離された時（permission=false）"""
        print(f"🗑️ 拒否処理開始: friend_id={self.friend_id}")
        
        # 即座にUIから削除
        self.parent_screen.list_layout.remove_widget(self)
        print("🗑️ UIから即座に削除しました")
        
        # 空リストチェック
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.check_empty_list(), 0.1)
        
        try:
            url = f"{SUPABASE_URL}/rest/v1/friend"
            params = {"friend_id": f"eq.{self.friend_id}"}
            data = {"permission": False}
            
            print(f"   URL: {url}")
            print(f"   Params: {params}")
            print(f"   Data: {data}")
            
            res = requests.patch(url, headers=headers, params=params, json=data, timeout=10)
            
            print(f"📡 拒否応答: status={res.status_code}")
            print(f"   Response: {res.text}")
            
            # 200と204を両方成功として扱う
            if res.status_code in [200, 204]:
                print("✅ 拒否成功（permission=false）")
            else:
                print(f"❌ 拒否失敗: {res.status_code}")
                # 失敗したら元に戻す
                if self.parent_screen and self.parent_screen.list_layout:
                    # 空メッセージを削除してからアイテムを追加
                    for child in self.parent_screen.list_layout.children[:]:
                        if isinstance(child, Label):
                            self.parent_screen.list_layout.remove_widget(child)
                    self.parent_screen.list_layout.add_widget(self)
                    instance.bg_color_instruction.rgba = self.del_btn_original_color
                    self.add_btn.disabled = False
                    self.del_btn.disabled = False
        except Exception as e:
            print(f"❌ 拒否エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラー時も元に戻す
            if self.parent_screen and self.parent_screen.list_layout:
                # 空メッセージを削除してからアイテムを追加
                for child in self.parent_screen.list_layout.children[:]:
                    if isinstance(child, Label):
                        self.parent_screen.list_layout.remove_widget(child)
                self.parent_screen.list_layout.add_widget(self)
                instance.bg_color_instruction.rgba = self.del_btn_original_color
                self.add_btn.disabled = False
                self.del_btn.disabled = False
    
    def check_empty_list(self):
        """リストが空になったら"未承認の申請はありません"を表示"""
        if len(self.parent_screen.list_layout.children) == 0:
            msg = Label(
                text="未承認の申請はありません",
                font_name="Japanese",
                font_size=Ssp(18),
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=Sdp(60),
            )
            self.parent_screen.list_layout.add_widget(msg)
            print("📝 空メッセージを表示しました")

# メイン画面
class FriendRequestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.current_user_mail = load_current_user_mail()
        self.root_layout = BoxLayout(orientation="vertical", spacing=Sdp(20), padding=Sdp(10))

        header = Label(
            text="フレンドリクエスト",
            size_hint=(1, None),
            height=Sdp(80),
            font_size=Ssp(40),
            font_name="Japanese",
            color=(0, 0, 0, 1),
        )
        self.root_layout.add_widget(header)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.list_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=Sdp(20),
            padding=Sdp(20)
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))

        self.scroll.add_widget(self.list_layout)
        self.root_layout.add_widget(self.scroll)

        self.add_widget(self.root_layout)

        # 最初の描画
        self.refresh_requests()

    def refresh_requests(self):
        """申請リストを再読み込み"""
        print("\n🔄 申請リストをリフレッシュ中...")
        self.list_layout.clear_widgets()

        if not self.current_user_mail:
            msg = Label(
                text="ログイン情報が見つかりません\n先にログインしてください",
                font_name="Japanese",
                font_size=Ssp(18),
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=Sdp(80),
            )
            self.list_layout.add_widget(msg)
            return

        pending = get_received_requests(self.current_user_mail)
        
        if not pending:
            msg = Label(
                text="未承認の申請はありません",
                font_name="Japanese",
                font_size=Ssp(18),
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=Sdp(60),
            )
            self.list_layout.add_widget(msg)
            return

        print(f"📋 {len(pending)}件の申請を表示します")
        
        for req in pending:
            sender_mail = req.get("send_user")
            friend_id = req.get("friend_id")
            
            print(f"   - sender_mail={sender_mail}, friend_id={friend_id}")
            
            sender_info = get_user_info_by_mail(sender_mail)
            
            if sender_info:
                name = sender_info.get("user_name", "不明")
                icon_url = sender_info.get("icon_url", "")
                
                print(f"     ✅ 表示: {name}")
                
                self.list_layout.add_widget(
                    FriendItem(
                        name=name,
                        img_src=icon_url,
                        friend_id=friend_id,
                        sender_mail=sender_mail,
                        parent_screen=self
                    )
                )
            else:
                print(f"     ⚠️ ユーザー情報が取得できませんでした")

    def on_enter(self):
        """画面表示時にキーボードイベントをバインド & リフレッシュ"""
        Window.bind(on_keyboard=self.on_back_button)
        # 画面に戻ってきたときは常に最新データを表示
        self.refresh_requests()
    
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