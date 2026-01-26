from kivy.config import Config
# Kivy 内蔵の仮想キーボード（黒い小さなキーボード）を使わず、OS の IME を使う
Config.set('kivy', 'keyboard_mode', 'system')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.text import LabelBase
from kivy.core.window import Window
try:
    Window.softinput_mode = 'below_target'
except Exception:
    pass
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.popup import Popup
from account import AccountScreen
from picture import PictureScreen
from map import MainScreen
from kivy.clock import Clock
# settingsは後でインポート（ログイン後にユーザー情報が必要なため）
import requests
import json
import hashlib


LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")

# Supabase設定
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"


class LoginForm(BoxLayout):
    def __init__(self, screen_manager=None, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
        self.app_instance = app_instance
        self.orientation = "vertical"
        self.size_hint = (None, None)
        
        Window.bind(size=self.update_size)
        self.update_size()
        
    def update_size(self, *args):
        # 画面幅の80%を使用（最小280px、最大400px）
        window_width = Window.width
        self.width = max(min(window_width * 0.8, dp(400)), dp(280))
        
        # 画面サイズに応じたパディングとスペーシング
        if window_width < dp(400):
            # スマホ
            self.padding = [dp(15), dp(20), dp(15), dp(20)]
            self.spacing = dp(15)
        else:
            # PC/タブレット
            self.padding = [dp(20), dp(30), dp(20), dp(30)]
            self.spacing = dp(20)
        
        # 高さを自動調整
        self.height = dp(450) if window_width < dp(400) else dp(500)
        
        # UIを再構築
        if self.children:
            self.build_ui()
    
    def build_ui(self):
        """UIコンポーネントを構築"""
        self.clear_widgets()

        # 画面幅に応じたフォントサイズ
        is_mobile = Window.width < dp(400)
        title_font_size = sp(22) if is_mobile else sp(26)
        normal_font_size = sp(14) if is_mobile else sp(16)

        # タイトル
        title = Label(
            text="待ち合わせアプリ",
            font_name="Japanese",
            font_size=title_font_size,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=dp(50) if is_mobile else dp(60),
        )
        self.add_widget(title)
        
        self.add_widget(Widget(size_hint_y=None, height=dp(15) if is_mobile else dp(20)))

        # メールアドレス入力
        self.email = TextInput(
            hint_text="メールアドレス",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(1, None),
            height=dp(45),
            multiline=False,
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.add_widget(self.email)

        # パスワード入力
        self.password = TextInput(
            hint_text="パスワード",
            font_name="Japanese",
            font_size=normal_font_size,
            password=True,
            size_hint=(1, None),
            height=dp(45),
            multiline=False,
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.add_widget(self.password)

        self.add_widget(Widget(size_hint_y=None, height=dp(10) if is_mobile else dp(15)))

        # ログインボタン
        login_btn = Button(
            text="ログイン",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(0.7 if is_mobile else 0.6, None),
            pos_hint={'center_x': 0.5},
            background_normal='',
            height=dp(45),
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        
        # 角丸背景
        with login_btn.canvas.before:
            self.login_bg_color = Color(rgba=get_color_from_hex('#ABE782'))
            self.login_rect = RoundedRectangle(pos=login_btn.pos, size=login_btn.size, radius=[dp(10)])
        
        def update_login_rect(instance, value):
            self.login_rect.pos = instance.pos
            self.login_rect.size = instance.size
            self.login_rect.radius = [dp(10)]

        login_btn.bind(pos=update_login_rect, size=update_login_rect)

        def on_login_press(instance):
            self.login_bg_color.rgba = get_color_from_hex('#9DCB6E')

        def on_login_release(instance):
            self.login_bg_color.rgba = get_color_from_hex('#ABE782')
            # ログイン処理を実行
            self.handle_login()

        login_btn.bind(on_press=on_login_press, on_release=on_login_release)

        self.add_widget(login_btn)

        # アカウント作成ボタン
        signup_btn = Button(
            text="アカウント作成",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(0.7 if is_mobile else 0.6, None),
            pos_hint={'center_x': 0.5},
            height=dp(45),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        
        with signup_btn.canvas.before:
            self.signup_bg_color = Color(rgba=get_color_from_hex('#ABE782'))
            self.signup_rect = RoundedRectangle(pos=signup_btn.pos, size=signup_btn.size, radius=[dp(10)])
        
        def update_signup_rect(instance, value):
            self.signup_rect.pos = instance.pos
            self.signup_rect.size = instance.size
            self.signup_rect.radius = [dp(10)]

        signup_btn.bind(pos=update_signup_rect, size=update_signup_rect)

        def on_signup_press(instance):
            self.signup_bg_color.rgba = get_color_from_hex('#9DCB6E')

        def on_signup_release(instance):
            self.signup_bg_color.rgba = get_color_from_hex('#ABE782')
            # 画面遷移
            if self.screen_manager:
                self.screen_manager.current = "account"

        signup_btn.bind(on_press=on_signup_press, on_release=on_signup_release)

        self.add_widget(signup_btn)
        self.add_widget(Widget(size_hint_y=None, height=dp(10)))
    
    def handle_login(self):
        """ログイン処理 (REST API版)"""
        email = self.email.text.strip()
        password = self.password.text.strip()

        if not email or not password:
            self.show_popup("入力エラー")
            return

        try:
            # 入力されたパスワードをハッシュ化
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            # Supabase REST API: usersテーブルを直接叩く
            url = f"{SUPABASE_URL}/rest/v1/users"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            params = {
                "user_mail": f"eq.{email}",
                "user_pw": f"eq.{hashed_password}"
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                print(f"Supabase response: {data}")

                if data and len(data) > 0:
                    user = data[0]
                    
                    # ✅ 先にJSONを保存（マップ遷移前に必ず実行）
                    self.save_login_info(email, hashed_password)
                    print("✅ ログイン情報をusers.jsonに保存しました")

                    if self.app_instance:
                        self.app_instance.current_user = user
                        # JSONの保存が完了してからマップに遷移
                        self.app_instance.open_map_screen()
                else:
                    self.show_popup("入力エラー")
            else:
                print(f"Error: {response.status_code}, {response.text}")
                self.show_popup("入力エラー")

        except Exception as e:
            print(f"Login error: {str(e)}")
            self.show_popup("入力エラー")


    def save_login_info(self, email, password):
        """ログイン情報をJSONファイルに保存（パスワードは既にハッシュ化済み）"""
        login_data = {
            "user_mail": email,
            "user_pw": password  # 既にハッシュ化されているのでそのまま保存
        }
        try:
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump([login_data], f, ensure_ascii=False, indent=2)
            print("Login info saved to users.json")
        except Exception as e:
            print(f"Error saving login info: {str(e)}")

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


class LoginScreen(Screen):
    def __init__(self, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance

        Window.clearcolor = get_color_from_hex('#ECF4E8')

        # AnchorLayoutで中央配置
        from kivy.uix.anchorlayout import AnchorLayout
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        
        self.form = LoginForm(screen_manager=None, app_instance=app_instance)
        self.form.build_ui()
        anchor.add_widget(self.form)
        
        self.add_widget(anchor)
    
    def on_enter(self):
        self.form.screen_manager = self.manager


class WaitingApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ログイン中のユーザー情報を保持
        self.current_user = None
        self.main_screen = None
        self.screen_manager = None
        self.current_friend_id = None  # 待ち合わせ対象の友達ID
    
    def build(self):
        self.title = "待ち合わせアプリ"
        
        # ScreenManagerを作成して保存
        self.screen_manager = ScreenManager(transition=NoTransition())
        
        # ✅ 自動ログインチェック
        if self.check_auto_login():
            print("✅ 自動ログイン成功 - マップ画面へ")
            # マップ画面を最初に表示
            class MapScreen(Screen):
                def __init__(self, app_inst, **kwargs):
                    super().__init__(name="map", **kwargs)
                    # ★★★ main_screenを保存 ★★★
                    app_inst.main_screen = MainScreen(app_instance=app_inst, current_user=app_inst.current_user)
                    self.add_widget(app_inst.main_screen)
            
            map_screen = MapScreen(app_inst=self)
            self.screen_manager.add_widget(map_screen)
            self.screen_manager.current = "map"
        else:
            print("⚠️ 自動ログイン失敗 - ログイン画面へ")
            # ログイン画面を表示
            self.screen_manager.add_widget(LoginScreen(name="login", app_instance=self))
            self.screen_manager.add_widget(AccountScreen(name="account"))
            self.screen_manager.add_widget(PictureScreen(name="picture"))
            self.screen_manager.current = "login"
        
        return self.screen_manager
    
    def check_auto_login(self):
        """users.jsonが存在し、有効なログイン情報があるかチェック"""
        try:
            import os
            
            # users.jsonの存在チェック
            if not os.path.exists('users.json'):
                print("📂 users.json が存在しません")
                return False
            
            # users.jsonを読み込み
            with open('users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 users.json読み込み: {data}")
            
            if not data or len(data) == 0:
                print("⚠️ users.jsonが空です")
                return False
            
            # メールとパスワードハッシュを取得
            user_mail = data[0].get('user_mail')
            user_pw = data[0].get('user_pw')
            
            if not user_mail or not user_pw:
                print("⚠️ ログイン情報が不完全です")
                return False
            
            # Supabaseで認証確認
            url = f"{SUPABASE_URL}/rest/v1/users"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            params = {
                "user_mail": f"eq.{user_mail}",
                "user_pw": f"eq.{user_pw}"
            }
            
            print(f"🔍 自動ログイン認証中... user_mail={user_mail}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                users = response.json()
                print(f"📡 Supabase応答: {users}")
                
                if users and len(users) > 0:
                    # ユーザー情報を保存
                    self.current_user = users[0]
                    print(f"✅ 自動ログイン成功: {self.current_user.get('user_name')}")
                    return True
                else:
                    print("❌ ユーザーが見つかりません（削除済み?）")
                    return False
            else:
                print(f"❌ Supabase認証エラー: {response.status_code}")
                return False
                
        except FileNotFoundError:
            print("📂 users.json が見つかりません")
            return False
        except json.JSONDecodeError:
            print("❌ users.json の形式が不正です")
            return False
        except Exception as e:
            print(f"❌ 自動ログインエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def open_map_screen(self):
        """map画面を開く"""
        if isinstance(self.root, ScreenManager):
            if not self.root.has_screen("map"):
                class MapScreen(Screen):
                    def __init__(self, app_inst, **kwargs):
                        super().__init__(name="map", **kwargs)
                        # ★★★ main_screenを保存 ★★★
                        app_inst.main_screen = MainScreen(app_instance=app_inst, current_user=app_inst.current_user)
                        self.add_widget(app_inst.main_screen)
                
                map_screen = MapScreen(app_inst=self)
                self.root.add_widget(map_screen)
            
            self.root.current = "map"
        else:
            self.root.clear_widgets()
            self.main_screen = MainScreen(app_instance=self, current_user=self.current_user)
            self.root.add_widget(self.main_screen)
    
    def open_location_mode(self, friend_id=None):
        """場所指定モードを開く - friend_profile.pyから呼ばれる"""
        print(f"📍 open_location_mode called with friend_id: {friend_id}")
        print(f"📍 self.main_screen = {self.main_screen}")
        print(f"📍 self.screen_manager = {self.screen_manager}")
        
        # 友達IDを保存
        if friend_id:
            self.current_friend_id = friend_id
            print(f"📍 current_friend_id set to {friend_id}")
        
        # map画面に戻る
        if self.screen_manager:
            print(f"📍 Switching to map screen")
            self.screen_manager.current = 'map'
        
        # 少し遅延させてから場所指定モードを有効化
        def enable_mode(dt):
            print(f"📍 enable_mode callback called")
            print(f"📍 self.main_screen = {self.main_screen}")
            if self.main_screen:
                print(f"📍 Setting is_location_mode = True")
                self.main_screen.is_location_mode = True
                if friend_id:
                    self.main_screen.current_friend_id = friend_id
                print(f"✅ 場所指定モード ON (is_location_mode={self.main_screen.is_location_mode})")
            else:
                print("⚠️ main_screen が見つかりません")
        
        Clock.schedule_once(enable_mode, 0.2)
    
    def back_to_login(self):
        """ログイン画面に戻る（ログアウト）"""
        print("🚪 ログアウト処理開始")
        
        self.current_user = None  # ログアウト時にユーザー情報をクリア
        
        try:
            import os
            if os.path.exists('users.json'):
                os.remove('users.json')
                print("🗑️ users.json を削除しました（ログアウト）")
        except Exception as e:
            print(f"⚠️ users.json削除エラー: {e}")
        
        # ✅ 既存のすべてのスクリーンを削除（リソース解放）
        if isinstance(self.root, ScreenManager):
            screen_names = [screen.name for screen in self.root.screens[:]]  # コピーを作成
            print(f"🗑️ 既存のスクリーン削除: {screen_names}")
            for screen_name in screen_names:
                try:
                    screen = self.root.get_screen(screen_name)
                    # スクリーン内の定期処理などを停止
                    if hasattr(screen, 'on_leave'):
                        screen.on_leave()
                    self.root.remove_widget(screen)
                except Exception as e:
                    print(f"⚠️ スクリーン削除エラー ({screen_name}): {e}")
        
        # ✅ 新しいスクリーンを追加
        self.screen_manager.add_widget(LoginScreen(name="login", app_instance=self))
        self.screen_manager.add_widget(AccountScreen(name="account"))
        self.screen_manager.add_widget(PictureScreen(name="picture"))
        
        # ログイン画面に遷移
        self.screen_manager.current = "login"
        
        print("✅ ログイン画面に遷移しました")
        self.root.add_widget(self.screen_manager)

    # ======================================================
    # ここから修正版(チャット機能の画面遷移)
    # ======================================================

    def open_chat_list(self):
        """チャット一覧画面を開く"""
        from chat_screen import MainLayout

        if isinstance(self.root, ScreenManager):

            # 同じ画面がないかチェック
            if not self.root.has_screen("chat_list"):
                
                class ChatListScreen(Screen):
                    def __init__(self, app_inst, **kwargs):
                        super().__init__(name="chat_list", **kwargs)
                        # current_userからメールアドレスを取得してMainLayoutに渡す
                        user_mail = app_inst.current_user.get('user_mail') if app_inst.current_user else None
                        layout = MainLayout(app_instance=app_inst, user_mail=user_mail)
                        self.add_widget(layout)
                
                new_screen = ChatListScreen(app_inst=self)
                self.root.add_widget(new_screen)

            # 画面遷移
            self.root.current = "chat_list"


    def open_chat(self, my_user_mail, target_name):
        """個別チャット画面を開く"""
        from personal_chat_screen import ChatScreen

        if isinstance(self.root, ScreenManager):

            screen_name = f"chat_{my_user_mail}_{target_name}"

            if not self.root.has_screen(screen_name):

                class PersonalChatScreen(Screen):
                    def __init__(self, my_user_mail, target_name, app_inst, **kwargs):
                        super().__init__(name=screen_name, **kwargs)
                        chat = ChatScreen(my_user_mail, target_name, app_instance=app_inst)
                        self.add_widget(chat)

                new_screen = PersonalChatScreen(my_user_mail, target_name, app_inst=self)
                self.root.add_widget(new_screen)

            # 画面遷移
            self.root.current = screen_name


    def back_to_list(self):
        """チャット一覧に戻る"""
        self.open_chat_list()


    def back_to_map(self):
        """マップ画面に戻る"""
        if isinstance(self.root, ScreenManager) and self.root.has_screen("map"):
            self.root.current = "map"
        else:
            from map import MainScreen
            self.root.clear_widgets()
            self.main_screen = MainScreen(app_instance=self, current_user=self.current_user)
            self.root.add_widget(self.main_screen)


    def open_settings(self):
            """設定画面を開く"""
            # settingsモジュールをここでインポート（ログイン後に呼ばれるため）
            from settings import SettingsScreen
            
            if isinstance(self.root, ScreenManager):
                if not self.root.has_screen("settings"):
                    s = SettingsScreen(name="settings", app_instance=self)
                    self.root.add_widget(s)
                self.root.current = "settings"

            
    
    def open_friend_profile(self, friend_mail):
        """フレンドプロフィール画面を開く"""
        from friend_profile import FriendProfileScreen
        from kivy.core.window import Window
        
        if isinstance(self.root, ScreenManager):
            screen_name = f"friend_profile_{friend_mail}"
            
            if not self.root.has_screen(screen_name):
                class FriendProfileWrap(Screen):
                    def __init__(self, friend_mail, app_inst, **kwargs):
                        super().__init__(name=screen_name, **kwargs)
                        self.app_inst = app_inst
                        # ★★★ app_instanceを渡す ★★★
                        profile = FriendProfileScreen(friend_mail=friend_mail, app_instance=app_inst)
                        self.add_widget(profile)
                        # キーボードイベントをバインド
                        Window.bind(on_keyboard=self.on_back_button)
                    
                    def on_back_button(self, window, key, *args):
                        """戻るボタン処理"""
                        if key == 27 and self.manager and self.manager.current == self.name:
                            self.manager.current = "map"
                            return True
                        return False
                
                new_screen = FriendProfileWrap(friend_mail, app_inst=self)
                self.root.add_widget(new_screen)
            
            self.root.current = screen_name
    
    def open_meeting_map(self, friend_id):
        """待ち合わせ用のマップ画面を開く"""
        from map2 import MainScreen
        
        if isinstance(self.root, ScreenManager):
            screen_name = "meeting_map"
            
            if not self.root.has_screen(screen_name):
                class MeetingMapScreen(Screen):
                    def __init__(self, friend_id, app_inst, **kwargs):
                        super().__init__(name=screen_name, **kwargs)
                        self.friend_id = friend_id
                        self.main_screen = MainScreen(app_instance=app_inst, current_user=app_inst.current_user)
                        self.add_widget(self.main_screen)
                
                new_screen = MeetingMapScreen(friend_id, app_inst=self)
                self.root.add_widget(new_screen)
            
            self.root.current = screen_name
            print(f"🗺️ 友人 {friend_id} との待ち合わせ場所を指定してください")
    
    def open_friend_addition(self):
        """友だち追加画面を開く"""
        from addition import FriendApp  

        if isinstance(self.root, ScreenManager):

            screen_name = "friend_add"

            if not self.root.has_screen(screen_name):

                class FriendAddScreen(Screen):
                    def __init__(self, app_inst, **kwargs):
                        super().__init__(name=screen_name, **kwargs)

                        # キーワード引数として渡す
                        layout = FriendApp(app_instance=app_inst)
                        self.add_widget(layout)

                # Screen作成
                screen = FriendAddScreen(app_inst=self)
                self.root.add_widget(screen)

            # 画面を切り替える
            self.root.current = screen_name
            
    def open_picture(self, caller="settings"):
        """画像選択画面を開く"""
        if isinstance(self.root, ScreenManager):
            # まだ picture 画面が登録されていなければ追加
            if not self.root.has_screen("picture"):
                pic_screen = PictureScreen(name="picture")
                self.root.add_widget(pic_screen)

            # 呼び出し元を記録（必ず設定）
            pic_screen = self.root.get_screen("picture")
            pic_screen.caller = caller
            print(f"open_picture: caller={caller} を設定しました")

            # 画面遷移
            self.root.current = "picture"




if __name__ == "__main__":
    WaitingApp().run()