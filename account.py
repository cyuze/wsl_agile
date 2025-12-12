from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.image import Image
from kivy.uix.stencilview import StencilView
from kivy.graphics import Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.popup import Popup
import requests
import json

# Supabase接続情報（REST API使用）
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


class CircleImage(StencilView):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.source = source
        
        with self.canvas:
            StencilPush()
            Color(1, 1, 1, 1)
            self.mask = Ellipse(pos=self.pos, size=self.size)
            StencilUse()

        self.image = Image(
            source=source,
            size_hint=(None, None),
            size=self.size,
            pos=self.pos,
            allow_stretch=True,
            keep_ratio=False
        )
        self.add_widget(self.image)

        with self.canvas:
            StencilUnUse()
            StencilPop()

        self.bind(pos=self.update_mask, size=self.update_mask)

    def update_mask(self, *args):
        self.mask.pos = self.pos
        self.mask.size = self.size
        self.image.pos = self.pos
        self.image.size = self.size
    
    def update_source(self, new_source):
        """画像ソースを更新"""
        self.source = new_source
        self.image.source = new_source
        self.image.reload()


class AccountForm(BoxLayout):
    def __init__(self, screen_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
        self.orientation = "vertical"
        self.size_hint = (None, None)
        
        # 画像参照を初期化
        self.img = None
        self.current_image_path = './img/icon.png'
        
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
        self.height = dp(550) if window_width < dp(400) else dp(600)
        
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
        
        self.add_widget(Widget(size_hint_y=None, height=dp(10)))
        
        # ガイダンス
        guidance = Label(
            text="アカウントを作成してください",
            font_name="Japanese",
            font_size=normal_font_size,
            color=(0, 0, 0, 1),
            halign='left',
            valign='top',
            size_hint=(1, None),
            height=dp(30),
        )
        guidance.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
        self.add_widget(guidance)
        
        # ユーザー名入力
        self.user = TextInput(
            hint_text="ユーザー名を入力",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(1, None),
            height=dp(45),
            multiline=False,
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.add_widget(self.user)
        
        # パスワード入力
        self.password = TextInput(
            hint_text="パスワードを入力",
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

        # メールアドレス入力
        self.email = TextInput(
            hint_text="メールアドレスを入力",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(1, None),
            height=dp(45),
            multiline=False,
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.add_widget(self.email)

        self.add_widget(Widget(size_hint_y=None, height=dp(10)))
        
        # 画像選択エリア
        img_size = dp(80) if is_mobile else dp(100)
        
        row = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=img_size,
            spacing=dp(15),
        )
        
        # 画像が既に存在する場合は更新、なければ新規作成
        if self.img is None:
            self.img = CircleImage(source=self.current_image_path)
        else:
            # 既存の画像ソースを使用
            self.img.update_source(self.current_image_path)
        
        self.img.size = (img_size, img_size)

        button_holder = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=img_size
        )
        button_holder.add_widget(Widget())

        picture = Button(
            text="画像を選択",
            font_name="Japanese",
            font_size=normal_font_size,
            size_hint=(1, None),
            height=dp(40),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0, 0, 0, 1)
        )
        
        with picture.canvas.before:
            self.picture_bg_color = Color(rgba=get_color_from_hex('#ABE782'))
            self.picture_rect = RoundedRectangle(pos=picture.pos, size=picture.size, radius=[dp(10)])

        def update_picture_rect(instance, value):
            self.picture_rect.pos = instance.pos
            self.picture_rect.size = instance.size
            self.picture_rect.radius = [dp(10)]

        picture.bind(pos=update_picture_rect, size=update_picture_rect)

        def on_picture_press(instance):
            self.picture_bg_color.rgba = get_color_from_hex('#9DCB6E')

        def on_picture_release(instance):
            self.picture_bg_color.rgba = get_color_from_hex('#ABE782')
            # 画像選択画面に遷移
            if self.screen_manager:
                picture_screen = self.screen_manager.get_screen("picture")
                picture_screen.caller = "account"   # ← 呼び出し元を記録
                self.screen_manager.current = "picture"


        picture.bind(on_press=on_picture_press, on_release=on_picture_release)

        button_holder.add_widget(picture)
        button_holder.add_widget(Widget())
        
        row.add_widget(self.img)
        row.add_widget(button_holder)
        self.add_widget(row)

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

            user_name = self.user.text.strip()
            user_pw   = self.password.text.strip()
            user_mail = self.email.text.strip()
            icon_path = self.current_image_path

            if not user_name or not user_pw or not user_mail:
                self.show_popup("入力が不足しています")
                print("入力が不足しています")
                return

            self.register_user(user_name, user_pw, user_mail, icon_path)

        def register_user(user_name, user_pw, user_mail, icon_path):
            try:
                # 1. ファイル名を決定（メールアドレスベース、特殊文字を除去）
                safe_email = user_mail.replace('@', '_at_').replace('.', '_')
                file_name = f"{safe_email}_icon.png"

                # 2. 画像ファイルを読み込み
                with open(icon_path, "rb") as f:
                    image_data = f.read()
                
                # 3. Storage にアップロード（REST API使用）
                storage_url = f"{SUPABASE_URL}/storage/v1/object/icon/{file_name}"
                storage_headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "image/png",
                    "x-upsert": "true"
                }
                
                storage_response = requests.post(
                    storage_url,
                    headers=storage_headers,
                    data=image_data,
                    timeout=20
                )
                
                print(f"Storage upload: {storage_response.status_code}")
                
                if storage_response.status_code not in [200, 201]:
                    print(f"Storage error: {storage_response.text}")
                    self.show_popup("画像のアップロードに失敗")
                    return

                # 4. 公開 URL を生成
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/icon/{file_name}"
                print("Public URL:", public_url)

                # 5. users テーブルに insert（REST API使用）
                db_url = f"{SUPABASE_URL}/rest/v1/users"
                data = {
                    "user_name": user_name,
                    "user_pw": user_pw,
                    "user_mail": user_mail,
                    "icon_url": public_url
                }
                
                db_response = requests.post(
                    db_url,
                    headers=headers,
                    json=data,
                    timeout=20
                )
                
                print(f"DB insert: {db_response.status_code}")
                
                if db_response.status_code in [200, 201]:
                    self.show_popup("登録成功")
                    # ログイン画面に遷移
                    if self.screen_manager:
                        self.screen_manager.current = "login"
                else:
                    print(f"DB error: {db_response.text}")
                    self.show_popup("登録失敗")

            except FileNotFoundError:
                self.show_popup("画像ファイルが見つかりません")
                print("画像ファイルが見つかりません:", icon_path)
            except requests.exceptions.Timeout:
                self.show_popup("タイムアウトしました")
                print("タイムアウト")
            except requests.exceptions.RequestException as e:
                self.show_popup("ネットワークエラー")
                print("ネットワークエラー:", e)
            except Exception as e:
                self.show_popup("登録失敗")
                print("登録失敗:", e)
        
        # register_user関数をメソッドとして登録
        self.register_user = register_user

        signup_btn.bind(on_press=on_signup_press, on_release=on_signup_release)

        self.add_widget(signup_btn)
        self.add_widget(Widget(size_hint=(1, None), height=dp(10)))
    
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

    def update_icon_image(self, image_path):
        """アイコン画像を更新"""
        self.current_image_path = image_path
        if self.img is not None:
            self.img.update_source(image_path)
            


class AccountScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.clearcolor = get_color_from_hex('#ECF4E8')

        # AnchorLayoutで中央配置
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        
        self.form = AccountForm(screen_manager=None)
        self.form.build_ui()
        anchor.add_widget(self.form)
        
        self.add_widget(anchor)
        
        # Androidの戻るボタンをキャッチ
        Window.bind(on_keyboard=self.on_back_button)
    
    def on_enter(self):
        # 画面に入った時にscreen_managerを設定
        self.form.screen_manager = self.manager
    
    def on_back_button(self, window, key, *args):
        """Androidの戻るボタン処理"""
        # key=27 が ESC / Android 戻るボタン
        if key == 27:
            if self.manager and self.manager.current == "account":
                self.manager.current = "login"
                return True  # イベントを消費（アプリ終了しない）
        return False