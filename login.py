from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from account import AccountScreen
from picture import PictureScreen



LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")

class LoginForm(BoxLayout):
    def __init__(self, screen_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
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
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(12), dp(10), dp(12)]
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
            background_color=get_color_from_hex('#ECF4E8'),
            padding=[dp(10), dp(12), dp(10), dp(12)]
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


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.clearcolor = get_color_from_hex('#ECF4E8')

        # AnchorLayoutで中央配置
        from kivy.uix.anchorlayout import AnchorLayout
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        
        self.form = LoginForm(screen_manager=None)
        self.form.build_ui()
        anchor.add_widget(self.form)
        
        self.add_widget(anchor)
    
    def on_enter(self):
        # 画面に入った時にscreen_managerを設定
        self.form.screen_manager = self.manager


class WaitingApp(App):
    def build(self):
        self.title = "待ち合わせアプリ"
        
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(AccountScreen(name="account"))
        sm.add_widget(PictureScreen(name="picture"))
        
        return sm


if __name__ == "__main__":
    WaitingApp().run()