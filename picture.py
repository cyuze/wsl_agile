from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen

import os

# Android 判定
try:
    from android.permissions import request_permissions, Permission
    platform = "android"
except:
    platform = "pc"


# ==========================================================
#  サムネイル付き画像（選択付き）
# ==========================================================
class SelectableImage(BoxLayout):
    def __init__(self, source, on_select, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=0,
            spacing=0,
            **kwargs
        )

        self.on_select = on_select
        self.is_selected = False
        self.source = source

        # 背景 + 枠線
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            self.border_color = Color(0, 0, 0, 0)
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(2))

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        # ---- 画像全体を表示 ----
        self.image = Image(
            source=source, 
            allow_stretch=True, 
            keep_ratio=True,  # アスペクト比を維持して全体表示
            size_hint=(1, 1)
        )

        self.add_widget(self.image)
        self.bind(on_touch_down=self._on_touch)

    def _on_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.on_select(self)
            return True
        return False

    def select(self):
        self.is_selected = True
        self.border_color.rgba = (0, 0.6, 0.3, 1)

    def unselect(self):
        self.is_selected = False
        self.border_color.rgba = (0, 0, 0, 0)

    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)
        self.border.width = dp(2)


# ==========================================================
#  メイン画面
# ==========================================================
class ImageSelectScreen(BoxLayout):
    def __init__(self, screen_manager=None, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)

        self.screen_manager = screen_manager

        # 背景色
        with self.canvas.before:
            Color(*get_color_from_hex("#ECF4E8"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # 画面幅に応じたレイアウト調整
        Window.bind(size=self.update_layout)
        self.update_layout()

    def update_layout(self, *args):
        self.clear_widgets()
        
        # 画面幅に応じた設定
        is_mobile = Window.width < dp(600)
        
        self.add_widget(Widget(size_hint_y=None, height=dp(10) if is_mobile else dp(15)))

        # ==========================================================
        #  上部バー
        # ==========================================================
        top_bar = BoxLayout(
            size_hint=(1, None),
            height=dp(60) if is_mobile else dp(70),
            padding=[dp(15), dp(10), dp(15), dp(10)],
            spacing=dp(10)
        )

        top_bar.add_widget(Widget(size_hint_x=0.25))

        # ---- 選択ボタン ----
        self.done_btn = Button(
            text="選択",
            background_color=(0, 0, 0, 0),
            background_normal='',
            background_down='',
            color=(1, 1, 1, 1),
            font_size=sp(16) if is_mobile else sp(18),
            font_name="Japanese",
            size_hint=(0.5, 1),
        )

        with self.done_btn.canvas.before:
            self.btn_color = Color(0, 0.6, 0.3, 1)
            self.btn_rect = RoundedRectangle(pos=self.done_btn.pos, size=self.done_btn.size, radius=[dp(12)])

        with self.done_btn.canvas.after:
            self.btn_overlay_color = Color(0, 0, 0, 0)
            self.btn_overlay = RoundedRectangle(pos=self.done_btn.pos, size=self.done_btn.size, radius=[dp(12)])

        def update_btn_graphics(instance, value):
            self.btn_rect.pos = instance.pos
            self.btn_rect.size = instance.size
            self.btn_rect.radius = [dp(12)]
            self.btn_overlay.pos = instance.pos
            self.btn_overlay.size = instance.size
            self.btn_overlay.radius = [dp(12)]

        def on_press(instance):
            self.btn_overlay_color.rgba = (0, 0, 0, 0.3)

        def on_release(instance):
            self.btn_overlay_color.rgba = (0, 0, 0, 0)
            if self.selected_item:
                print("選択:", self.selected_item.source)
                if self.screen_manager:
                    picture_screen = self.screen_manager.get_screen("picture")
                    caller = picture_screen.caller

                    if caller == "account":
                        account_screen = self.screen_manager.get_screen("account")
                        account_screen.form.update_icon_image(self.selected_item.source)
                        self.screen_manager.current = "account"

                    elif caller == "settings":
                        settings_screen = self.screen_manager.get_screen("settings")
                        settings_screen.update_user_icon(self.selected_item.source)   # DB更新
                        settings_screen.update_icon_image(self.selected_item.source)  # UI更新
                        self.screen_manager.current = "settings"


            else:
                print("画像未選択")


        self.done_btn.bind(pos=update_btn_graphics, size=update_btn_graphics)
        self.done_btn.bind(on_press=on_press)
        self.done_btn.bind(on_release=on_release)

        top_bar.add_widget(self.done_btn)
        top_bar.add_widget(Widget(size_hint_x=0.25))

        self.add_widget(top_bar)
        self.add_widget(Widget(size_hint_y=None, height=dp(10) if is_mobile else dp(15)))

        # ==========================================================
        # 画像グリッド（レスポンシブ対応）
        # ==========================================================
        scroll = ScrollView(size_hint=(1, 1))
        
        # 画面幅に応じてカラム数を変更
        cols = 3
        grid_spacing = dp(10) if is_mobile else dp(15)
        grid_padding = dp(10) if is_mobile else dp(15)
        
        self.grid = GridLayout(
            cols=cols, 
            spacing=grid_spacing, 
            padding=grid_padding,
            size_hint_y=None
        )
        self.grid.bind(minimum_height=self.grid.setter('height'))

        self.selected_item = None

        folder = self.get_image_folder()
        print("使用フォルダ:", folder)

        if os.path.isdir(folder):
            files = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            
            for file in files:
                path = os.path.join(folder, file)
                # 画像サイズを画面幅に応じて調整
                img_size = (Window.width - grid_padding * 2 - grid_spacing * (cols - 1)) / cols
                img_widget = SelectableImage(path, self.on_select_image)
                img_widget.height = img_size
                self.grid.add_widget(img_widget)

        scroll.add_widget(self.grid)
        self.add_widget(scroll)

    # Android 写真フォルダ探索
    def get_image_folder(self):
        if platform == "android":
            candidates = [
                "/sdcard/DCIM/Camera",
                "/sdcard/Pictures",
                "/storage/emulated/0/DCIM/Camera",
                "/storage/emulated/0/Pictures",
            ]
            for p in candidates:
                if os.path.isdir(p) and len(os.listdir(p)) > 0:
                    return p
            return "/sdcard/DCIM"

        return "./img"

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def on_select_image(self, item):
        if self.selected_item:
            self.selected_item.unselect()
        self.selected_item = item
        item.select()


# ==========================================================
#  Screen用のラッパー
# ==========================================================
class PictureScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.caller = None

        Window.clearcolor = get_color_from_hex('#ECF4E8')

        self.image_select = ImageSelectScreen(screen_manager=None)
        self.add_widget(self.image_select)
        Window.bind(on_keyboard=self.on_back_button)
        
    
    def on_enter(self):
        # 画面に入った時にscreen_managerを設定
        self.image_select.screen_manager = self.manager
        

    def on_back_button(self, window, key, *args):
        """Androidの戻るボタン処理"""
        # key=27 が ESC / Android 戻るボタン
        if key == 27 and self.caller == "account":
            # account → picture → 戻る → account
            self.manager.current = "account"
            return True
        elif key == 27 and self.caller == "settings":
            # settings → picture → 戻る → settings
            self.manager.current = "settings"
            return True
        return False
