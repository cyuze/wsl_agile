import os
import json
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
from kivy.graphics import (
    Color,
    Ellipse,
    StencilPush,
    StencilUse,
    StencilUnUse,
    StencilPop,
    RoundedRectangle,
)
from kivy.metrics import dp, sp
import requests
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from picture import PictureScreen

from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput


SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def get_user_by_mail(user_mail: str):
    url = f"{SUPABASE_URL}/rest/v1/users"
    params = {"select": "user_id,user_name,icon_url", "user_mail": f"eq.{user_mail}"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        raise Exception(f"Supabase error {res.status_code}: {res.text}")
    data = res.json()
    if not data:
        return None
    return data[0]

LabelBase.register(name="Japanese", fn_regular="NotoSansJP-Regular.ttf")
Window.clearcolor = (236 / 255, 244 / 255, 232 / 255, 1)

# === スケーリング関数 ===
scale = Window.dpi / 160.0  # 160dpiを基準に拡大


def Sdp(value):
    return dp(value * scale)


def Ssp(value):
    return sp(value * scale)


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
            size=self.size,
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
        self.background_normal = ""
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
        self.app_instance = app_instance

        # 初期値
        self.user_name = ""
        self.img_url = ""

        # UI構築
        self.build_ui()

    def on_pre_enter(self):
        """画面に入るたびに最新の users.json を読み込む"""
        self.load_user_info()

    def load_user_info(self):
        """users.json を安全に読み込み、Supabase から最新情報を取得して UI を更新"""
        try:
            json_path = os.path.join(os.path.dirname(__file__), "users.json")

            # ファイルが存在しない場合は自動生成
            if not os.path.exists(json_path):
                print("users.json が存在しません → 初期ファイルを作成します")
                default_data = [{
                    "user_mail": "guest",
                    "user_pw": ""
                }]
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)

            # JSON 読み込み
            with open(json_path, "r", encoding="utf-8") as f:
                users = json.load(f)

            user_mail = users[0].get("user_mail", "guest")

            # Supabase からユーザー情報取得
            row = get_user_by_mail(user_mail)
            if row:
                self.user_name = row["user_name"]
                self.img_url = row["icon_url"]
            else:
                self.user_name = "ゲストユーザー"
                self.img_url = "img/cat_placeholder.png"

            # UI 更新
            self.name_label.text = self.user_name
            self.profile_icon.img.source = self.img_url
            self.profile_icon.img.reload()

        except Exception as e:
            print("設定画面のユーザー情報更新エラー:", e)



    def build_ui(self):
        # ... 既存のUI構築コード ...
        Window.clearcolor = (236 / 255, 244 / 255, 232 / 255, 1)

        Window.bind(on_keyboard=self.on_back_button)

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
                **kw,
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
                **kw,
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
            size_hint_y=None,
        )
        root_layout.bind(minimum_height=root_layout.setter("height"))

        # 以下はスクロール対象の要素
        root_layout.add_widget(left_label("アカウント編集"))

        # プロフィール
        profile_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(100),
            size_hint_y=None,
            height=Sdp(160),
        )
        profile_layout.add_widget(Widget(size_hint_x=0.3))
        
        self.profile_icon = CircleImageView(
            source=self.img_url,
            size_hint=(None, None),
            size=(Sdp(120), Sdp(120))
        )

        profile_layout.add_widget(self.profile_icon)
        self.name_label = Label(
            text=self.user_name,
            font_size=Ssp(32),
            color=(0, 0, 0, 1),
            font_name="Japanese",
            size_hint=(None, None),
            height=Sdp(80),
        )

        profile_layout.add_widget(self.name_label)
        profile_layout.add_widget(Widget(size_hint_x=1))
        root_layout.add_widget(profile_layout)

        # 編集ボタン
        edit_layout = AnchorLayout(
            anchor_x="center", anchor_y="bottom", size_hint_y=None, height=Sdp(80)
        )
        inner_layout = BoxLayout(
            orientation="horizontal",
            spacing=Sdp(60),
            size_hint=(None, None),
            width=Sdp(360),
            height=Sdp(80),
        )
        edit_button1 = RoundedButton(
            text="編集",
            size_hint=(None, None),
            color=(0, 0, 0, 1),
            size=(Sdp(140), Sdp(70)),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_imgEdit_press,
        )
        edit_button2 = RoundedButton(
            text="編集",
            size_hint=(None, None),
            color=(0, 0, 0, 1),
            size=(Sdp(140), Sdp(70)),
            font_name="Japanese",
            font_size=Ssp(24),
            on_press=self.on_nameEdit_press,
        )
        inner_layout.add_widget(edit_button1)
        inner_layout.add_widget(edit_button2)
        edit_layout.add_widget(inner_layout)
        root_layout.add_widget(edit_layout)

        # 通知
        root_layout.add_widget(left_label("通知"))
        notif_layout = GridLayout(
            cols=2, spacing=Sdp(20), size_hint_y=None, height=Sdp(160)
        )
        notif_layout.add_widget(left_label("位置情報関係"))
        notif_layout.add_widget(Switch(active=True))
        notif_layout.add_widget(left_label("待ち合わせ時間"))
        notif_layout.add_widget(Switch(active=False))
        root_layout.add_widget(notif_layout)

        # プライバシー
        root_layout.add_widget(left_label("プライバシー"))
        privacy_layout = GridLayout(
            cols=2, spacing=Sdp(20), size_hint_y=None, height=Sdp(80)
        )
        privacy_layout.add_widget(left_label("位置情報の表示"))
        privacy_layout.add_widget(Switch(active=True))
        root_layout.add_widget(privacy_layout)

        # 確定
        root_layout.add_widget(
            RoundedButton(
                text="確定",
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=Sdp(70),
                font_name="Japanese",
                font_size=Ssp(24),
                on_press=self.on_submit_press,
            )
        )
        root_layout.add_widget(
            RoundedButton(
                text="ログアウト",
                color=(0, 0, 0, 1),
                size_hint_y=None,
                height=Sdp(70),
                font_name="Japanese",
                font_size=Ssp(24),
                on_press=self.on_logout_press,
            )
        )

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
        """名前編集ボタンが押されたときの処理"""
        print("名前編集ボタンが押されました。編集ダイアログを表示します。")
        self.show_name_edit_dialog()

    def show_name_edit_dialog(self):
        """名前編集用のポップアップダイアログを表示"""
        # レイアウト作成
        content = BoxLayout(
            orientation='vertical',
            padding=Sdp(20),
            spacing=Sdp(15)
        )
        
        # 説明ラベル
        label = Label(
            text='新しい名前を入力してください',
            font_name='Japanese',
            size_hint_y=None,
            height=Sdp(40),
            color=(0, 0, 0, 1),
            font_size=Ssp(24)
        )
        content.add_widget(label)
        
        # テキスト入力欄
        text_input = TextInput(
            text=self.user_name,
            multiline=False,
            size_hint_y=None,
            height=Sdp(50),
            font_size=Ssp(24),
            font_name='Japanese',
            padding=[Sdp(10), Sdp(10)]
        )
        content.add_widget(text_input)
        
        # ボタンレイアウト
        button_layout = BoxLayout(
            orientation='horizontal',
            spacing=Sdp(15),
            size_hint_y=None,
            height=Sdp(60)
        )
        
        # キャンセルボタン
        cancel_btn = RoundedButton(
            text='キャンセル',
            font_name='Japanese',
            font_size=Ssp(20),
            color=(0, 0, 0, 1)
        )
        
        # 保存ボタン
        save_btn = RoundedButton(
            text='保存',
            font_name='Japanese',
            font_size=Ssp(20),
            color=(0, 0, 0, 1)
        )
        
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(save_btn)
        content.add_widget(button_layout)
        
        # ポップアップ作成
        popup = Popup(
            title='名前の変更',
            title_font='Japanese',
            title_size=Ssp(28),
            content=content,
            size_hint=(0.8, None),
            height=Sdp(250),
            separator_color=(0.671, 0.906, 0.510, 1)
        )
        
        # ボタンのイベント設定
        cancel_btn.bind(on_press=popup.dismiss)
        save_btn.bind(on_press=lambda x: self.save_new_name(text_input.text, popup))
        
        popup.open()

    def save_new_name(self, new_name, popup):
        """新しい名前をSupabaseに保存"""
        try:
            # 空白チェック
            if not new_name or not new_name.strip():
                print("❌ 名前が空です")
                return
            
            new_name = new_name.strip()
            
            # users.jsonから現在のユーザーメールを取得
            json_path = os.path.join(os.path.dirname(__file__), "users.json")
            
            if not os.path.exists(json_path):
                print("❌ users.json が見つかりません")
                return
            
            with open(json_path, "r", encoding="utf-8") as f:
                users = json.load(f)
            
            user_mail = users[0].get("user_mail", "guest")
            
            # Supabaseのusersテーブルを更新
            db_url = f"{SUPABASE_URL}/rest/v1/users"
            params = {"user_mail": f"eq.{user_mail}"}
            payload = {"user_name": new_name}
            
            res = requests.patch(db_url, headers=headers, params=params, json=payload)
            
            if res.status_code in [200, 204]:
                print(f"✅ 名前を更新しました: {new_name}")
                
                # ローカルの情報も更新
                self.user_name = new_name
                self.name_label.text = new_name
                
                # ポップアップを閉じる
                popup.dismiss()
                
                # 成功メッセージ（オプション）
                self.show_success_message("名前を変更しました")
            else:
                print(f"❌ DB error: ステータス {res.status_code}")
                print(f"レスポンス: {res.text}")
                self.show_error_message("名前の変更に失敗しました")
        
        except Exception as e:
            print(f"❌ 名前更新エラー: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_message("エラーが発生しました")

    def show_success_message(self, message):
        """成功メッセージを表示"""
        content = BoxLayout(orientation='vertical', padding=Sdp(20))
        content.add_widget(Label(
            text=message,
            font_name='Japanese',
            font_size=Ssp(24),
            color=(1, 1, 1, 1)
        ))
        
        popup = Popup(
            title='成功',
            title_font='Japanese',
            content=content,
            size_hint=(0.7, None),
            separator_color=(0.671, 0.906, 0.510, 1),
            height=Sdp(150)
        )
        
        # 1.5秒後に自動で閉じる
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)
        popup.open()

    def show_error_message(self, message):
        """エラーメッセージを表示"""
        content = BoxLayout(orientation='vertical', padding=Sdp(20))
        content.add_widget(Label(
            text=message,
            font_name='Japanese',
            font_size=Ssp(24),
            color=(1, 1, 1, 1)
        ))
        
        popup = Popup(
            title='エラー',
            title_font='Japanese',
            content=content,
            separator_color=(0.671, 0.906, 0.510, 1),
            size_hint=(0.7, None),
            height=Sdp(150)
        )
        
        # 2秒後に自動で閉じる
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)
        popup.open()

    def on_logout_press(self, instance):
        """ログアウトボタンが押された瞬間（色を暗くする）"""
        # ボタンの色を50%暗くする
        if hasattr(instance, 'bg_color_instruction'):
            if not hasattr(self, 'logout_original_color'):
                self.logout_original_color = instance.bg_color_instruction.rgba
            
            instance.bg_color_instruction.rgba = (
                self.logout_original_color[0] * 0.5,
                self.logout_original_color[1] * 0.5,
                self.logout_original_color[2] * 0.5,
                1
            )
        
        print("🚪 ログアウトボタンが押されました")
        
        # 少し遅延してからログアウト処理
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.do_logout(instance), 0.2)

    def do_logout(self, instance):
        """実際のログアウト処理"""
        try:
            import os
            
            # users.jsonを削除
            if os.path.exists('users.json'):
                os.remove('users.json')
                print("🗑️ users.json を削除しました（ログアウト）")
            else:
                print("⚠️ users.json が存在しません")
            
            # app_instanceのback_to_loginを呼び出す
            if self.app_instance and hasattr(self.app_instance, 'back_to_login'):
                print("📱 ログイン画面へ遷移します")
                self.app_instance.back_to_login()
            else:
                print("❌ app_instance が見つかりません")
        
        except Exception as e:
            print(f"❌ ログアウトエラー: {e}")
            import traceback
            traceback.print_exc()

    def on_submit_press(self, instance):
        print("確定ボタンが押されました。変更内容を確定します。")

    def update_icon_image(self, image_path):
        """設定画面のアイコン画像を更新"""
        if self.profile_icon:
            # キャッシュバスター付きで更新
            import time
            if "?" in image_path:
                # すでにクエリパラメータがある場合
                new_path = f"{image_path}&reload={int(time.time())}"
            else:
                new_path = f"{image_path}?t={int(time.time())}"
            
            self.profile_icon.img.source = new_path
            self.profile_icon.img.reload()
            print(f"🖼️ UIアイコン更新: {new_path}")

    def update_user_icon(self, icon_path):
        """ログイン中ユーザーのアイコンを更新"""
        try:
            # users.jsonからユーザー情報を取得
            json_path = os.path.join(os.path.dirname(__file__), "users.json")
            
            if not os.path.exists(json_path):
                print("users.json が見つかりません")
                return False
                
            with open(json_path, "r", encoding="utf-8") as f:
                users = json.load(f)
            
            user_mail = users[0].get("user_mail", "guest")
            
            # Supabaseからユーザー情報取得
            row = get_user_by_mail(user_mail)
            if not row:
                print("ユーザー情報が取得できませんでした")
                return False
                
            user_name = row["user_name"]

            # ファイル名を決定
            safe_name = user_name.replace("@", "_at_").replace(".", "_")
            file_name = f"{safe_name}_icon.png"

            # 画像ファイル読み込み
            with open(icon_path, "rb") as f:
                image_data = f.read()

            # Storage にアップロード(上書き)
            storage_url = f"{SUPABASE_URL}/storage/v1/object/icon/{file_name}"
            storage_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/png",
                "x-upsert": "true",
            }
            res = requests.post(storage_url, headers=storage_headers, data=image_data)

            if res.status_code not in [200, 201]:
                print("Storage error:", res.status_code, res.text)
                return False

            # 公開 URL (キャッシュバスター付き)
            import time
            timestamp = int(time.time())
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/icon/{file_name}?t={timestamp}"

            # users テーブルを UPDATE
            db_url = f"{SUPABASE_URL}/rest/v1/users"
            params = {"user_name": f"eq.{user_name}"}
            payload = {"icon_url": public_url}
            res = requests.patch(db_url, headers=headers, params=params, json=payload)

            # 204 No Content も成功とみなす
            if res.status_code in [200, 204]:
                print("✅ アイコン更新成功")
                print(f"新しいURL: {public_url}")
                
                # ローカルの情報も更新
                self.img_url = public_url
                
                return True
            else:
                print(f"DB error: ステータス {res.status_code}")
                print(f"レスポンス: {res.text}")
                return False

        except Exception as e:
            print("更新失敗:", e)
            import traceback
            traceback.print_exc()
            return False


    def on_back_button(self, window, key, *args):
        if key == 27 and self.manager.current == "settings":
            print("戻るボタン: map に戻ります")
            if self.app_instance:
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
