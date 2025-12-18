from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.stencilview import StencilView
from kivy.uix.image import AsyncImage
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.core.text import LabelBase
from kivy.config import Config
import os
# システムのソフトキーボード（IME）を利用し、Kivy の仮想キーボードを使わない設定
Config.set('kivy', 'keyboard_mode', 'system')
from kivy.core.window import Window
# Android ではキーボードが入力欄の下に表示されるようにする（押し上げなし）
try:
    Window.softinput_mode = 'below_target'
except Exception:
    # 古い環境や非対応プラットフォームでは無視
    pass
from datetime import datetime
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.clock import Clock
import requests
import json


# 日本語フォント
LabelBase.register(name='NotoSansJP', fn_regular='NotoSansJP-Regular.ttf')

# ===== Supabase設定 =====
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"


# 円形マスク用のウィジェット
class CircularImage(StencilView):
    def __init__(self, source, size_val=60, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (size_val, size_val)
        self.source = source

        # === マスク円(Stencil) ===
        with self.canvas.before:
            StencilPush()
            self.mask = Ellipse(pos=self.pos, size=self.size)
            StencilUse()

        # === 内部画像 ===
        self.image = AsyncImage(
            source=self.source,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(None, None),
            size=self.size,
            pos=self.pos
        )
        self.add_widget(self.image)

        with self.canvas.after:
            StencilUnUse()
            StencilPop()

        self.bind(pos=self.update_mask, size=self.update_mask)

    def update_mask(self, *args):
        self.mask.pos = self.pos
        self.mask.size = self.size
        self.image.pos = self.pos
        self.image.size = self.size


# ===== メッセージバブル =====
class MessageBubble(BoxLayout):
    def __init__(self, text, time, is_sent=False, icon_url=None, is_image=False, **kwargs):
        # 長押し用の変数とmessage_idを先に取得
        self.message_id = kwargs.pop('message_id', None)
        self.is_image = is_image

        super().__init__(**kwargs)
        self.is_sent = is_sent
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = [10, 5, 10, 5]
        self.spacing = 10

        from kivy.clock import Clock
        self.touch_start_time = None
        self.long_press_event = None

        if is_sent:
            # 自分のメッセージ(右側)
            self.add_widget(Widget())
            message_box = BoxLayout(orientation='vertical', size_hint_x=None, spacing=2)
            
            if is_image:
                # 画像メッセージの場合
                bubble = AsyncImage(
                    source=text,  # textにはURL
                    size_hint=(None, None),
                    size=(300, 300),
                    allow_stretch=True,
                    keep_ratio=True
                )
                message_box.width = 300
            else:
                # テキストメッセージの場合
                bubble = Label(
                    text=text,
                    halign='right',
                    valign='top',
                    padding=[2, 2],
                    color=(0, 0, 0, 1),
                    font_name='NotoSansJP',
                    font_size='14sp',
                    size_hint=(None, None),
                    text_size=(None, None)
                )
            bubble.bind(texture_size=bubble.setter('size'))

            max_width = Window.width * 0.6

            # 初期テクスチャ更新で幅・高さを計算
            bubble.texture_update()
            text_width = bubble.texture_size[0] + 30
            text_height = bubble.texture_size[1] + 20

            # 最低幅を設けて、短いメッセージで時間ラベルと重ならないようにする
            min_width = 60
            desired_width = max(min_width, text_width)

            if desired_width > max_width:
                bubble.text_size = (max_width - 30, None)
                bubble.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + 20))
                message_box.width = max_width
            else:
                bubble.size = (desired_width, text_height)
                message_box.width = desired_width
            
            with bubble.canvas.before:
                Color(0.8, 0.95, 0.7, 1)
                self.bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[15])
            bubble.bind(pos=lambda i, v: setattr(self.bg, 'pos', i.pos))
            bubble.bind(size=lambda i, v: setattr(self.bg, 'size', i.size))

            # 時間表示(右揃え)
            time_label = Label(
                text=time,
                font_size='11sp',
                color=(0.4, 0.4, 0.4, 1),
                font_name='NotoSansJP',
                size_hint=(None, None),
                halign='right',
                valign='top'
            )
            time_label.bind(texture_size=time_label.setter('size'))
            # 時間は折返したくないため text_size は制約しない
            time_label.text_size = (None, None)
            time_label.texture_update()

            # 時刻表示が短いメッセージ幅に収まらない場合はコンテナ幅を広げる
            time_w = time_label.texture_size[0]
            if time_w + 6 > message_box.width:
                # 余白を少し追加して見やすくする
                new_width = min(max_width, time_w + 6)
                message_box.width = new_width
                # バブルが折返し設定でないときはバブル幅を合わせる
                if getattr(bubble, 'text_size', (None, None))[0] is None:
                    bubble.size = (message_box.width, bubble.size[1])
            
            message_box.add_widget(bubble)
            message_box.add_widget(time_label)
            
            message_box.height = bubble.height + time_label.height + 6
            self.height = message_box.height + 18
            
            self.add_widget(message_box)

        else:
            # 相手のメッセージ(左側)
            # 相手アイコンを少し小さめに調整（過剰に大きかったため）
            avatar = CircularImage(source=icon_url or "img/default.png", size_val=112)

            # アバターをトップに配置するための垂直レイアウト（上寄せ→中央揃えは既存のコンテナで）
            avatar_container = BoxLayout(orientation='vertical', size_hint=(None, 1), width=avatar.size[0])
            avatar_container.add_widget(Widget())
            avatar_container.add_widget(avatar)
            avatar_container.add_widget(Widget())

            message_box = BoxLayout(orientation='vertical', size_hint_x=None, spacing=2)
            
            if is_image:
                # 画像メッセージの場合
                bubble = AsyncImage(
                    source=text,  # textにはURL
                    size_hint=(None, None),
                    size=(300, 300),
                    allow_stretch=True,
                    keep_ratio=True
                )
                message_box.width = 300
            else:
                # テキストメッセージの場合
                bubble = Label(
                    text=text,
                    halign='left',
                    valign='top',
                    padding=[2, 2],
                    color=(0, 0, 0, 1),
                    font_name='NotoSansJP',
                    font_size='14sp',
                    size_hint=(None, None),
                    text_size=(None, None)
                )
            bubble.bind(texture_size=bubble.setter('size'))

            max_width = Window.width * 0.6

            bubble.texture_update()
            text_width = bubble.texture_size[0] + 30
            text_height = bubble.texture_size[1] + 20

            min_width = 60
            desired_width = max(min_width, text_width)

            if desired_width > max_width:
                bubble.text_size = (max_width - 30, None)
                bubble.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + 20))
                message_box.width = max_width
            else:
                bubble.size = (desired_width, text_height)
                message_box.width = desired_width
            
            with bubble.canvas.before:
                Color(0.92, 0.92, 0.92, 1)
                self.bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[15])
            bubble.bind(pos=lambda i, v: setattr(self.bg, 'pos', i.pos))
            bubble.bind(size=lambda i, v: setattr(self.bg, 'size', i.size))

            time_label = Label(
                text=time,
                font_size='11sp',
                color=(0.4, 0.4, 0.4, 1),
                font_name='NotoSansJP',
                size_hint=(None, None),
                halign='left'
            )
            time_label.bind(texture_size=time_label.setter('size'))
            time_label.text_size = (None, None)
            time_label.texture_update()

            # 時刻表示が短いメッセージ幅に収まらない場合はコンテナ幅を広げる
            time_w = time_label.texture_size[0]
            if time_w + 6 > message_box.width:
                new_width = min(max_width, time_w + 6)
                message_box.width = new_width
                if getattr(bubble, 'text_size', (None, None))[0] is None:
                    bubble.size = (message_box.width, bubble.size[1])

            message_box.add_widget(bubble)
            message_box.add_widget(time_label)
            
            message_box.height = bubble.height + time_label.height + 6
            self.height = max(message_box.height + 18, 60)

            self.add_widget(avatar_container)
            self.add_widget(message_box)
            self.add_widget(Widget())

    def on_touch_down(self, touch):
        # 自分のメッセージ（is_sent=True ＆ message_id がある場合）だけ長押し有効
        if getattr(self, "is_sent", False) and self.message_id and self.collide_point(*touch.pos):
            from kivy.clock import Clock
            self.touch_start_time = Clock.get_time()
            self.long_press_event = Clock.schedule_once(
                lambda dt: self.show_delete_dialog(), 0.5
            )
        return super().on_touch_down(touch)


    def on_touch_up(self, touch):
        if self.long_press_event:
            self.long_press_event.cancel()
            self.long_press_event = None
        return super().on_touch_up(touch)

    def show_delete_dialog(self):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(
            text='メッセージを削除しますか?',
            font_name='NotoSansJP',
            font_size='16sp',
            color=(1, 1, 1, 1)
        ))
        
        btn_layout = BoxLayout(size_hint_y=None, height=80, spacing=10)
        
        # ChatScreenインスタンスを探す
        chat_screen = self.parent
        while chat_screen and not isinstance(chat_screen, ChatScreen):
            chat_screen = chat_screen.parent
        
        def delete_message(instance):
            if chat_screen:
                chat_screen.delete_message(self.message_id, self)
            popup.dismiss()
        
        def cancel(instance):
            popup.dismiss()
        
        btn_delete = Button(
            text='削除',
            font_name='NotoSansJP',
            background_color=(1, 0.3, 0.3, 1)
        )
        btn_delete.bind(on_press=delete_message)
        
        btn_cancel = Button(
            text='キャンセル',
            font_name='NotoSansJP'
        )
        btn_cancel.bind(on_press=cancel)
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_delete)
        content.add_widget(btn_layout)
        
        popup = Popup(
            title='メッセージ削除',
            content=content,
            size_hint=(0.8, 0.3),
            title_font='NotoSansJP'
        )
        popup.open()


class ImageButton(ButtonBehavior, Image):
    pass


# ===== チャット画面 =====
class ChatScreen(BoxLayout):
    def __init__(self, my_id, target_id, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.my_id = my_id
        self.target_id = target_id
        self.app_instance = app_instance

        # ヘッダー(相手の名前とアイコン表示)
        header = BoxLayout(size_hint_y=None, height=140, padding=[10, 5], spacing=10)
        with header.canvas.before:
            Color(0.796, 0.953, 0.733, 1)
            self.header_rect = RoundedRectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda i, v: setattr(self.header_rect, 'pos', i.pos))
        header.bind(size=lambda i, v: setattr(self.header_rect, 'size', i.size))
        
        with header.canvas.after:
            Color(0, 0, 0, 1)  # 黒色
            self.header_line = RoundedRectangle(
                pos=(header.x, header.y), 
                size=(header.width, 4)  # 線の太さ（2ピクセル）
            )

        header.bind(pos=lambda i, v: setattr(self.header_rect, 'pos', i.pos))
        header.bind(size=lambda i, v: setattr(self.header_rect, 'size', i.size))

        # 線の位置とサイズも連動させる
        header.bind(
            pos=lambda i, v: setattr(self.header_line, 'pos', (i.x, i.y)),
            size=lambda i, v: setattr(self.header_line, 'size', (i.width, 2))
        )
        
        # (ユーザー情報を取得してからアイコンを作成します)

        # 相手の情報を取得
        url = f"{SUPABASE_URL}/rest/v1/users"
        params = {
            "select": "user_name,icon_url",
            "user_id": f"eq.{target_id}"
        }
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                user_data = res.json()
                if user_data:
                    other_name = user_data[0]['user_name']
                    icon_url = user_data[0].get('icon_url')
                else:
                    other_name = "不明"
                    icon_url = None
            else:
                other_name = "不明"
                icon_url = None
        except Exception as e:
            print(f"❌ ユーザー情報取得エラー: {e}")
            other_name = "不明"
            icon_url = None
        
        self.other_icon_url = icon_url
        
        # タイトルコンテナ(テキストのみ)
        title_container = BoxLayout(orientation='horizontal', size_hint_x=1, spacing=8, padding=[0, 8])

        name_label = Label(
            text=f'{other_name}と会話中',
            font_size='27sp',
            font_name='NotoSansJP',
            color=(0, 0, 0, 1),
            size_hint_x=1,
            halign='left'
        )

        # 左側に少しスペースを置き、タイトルのみを表示
        title_container.add_widget(Widget(size_hint_x=None, width=12))
        title_container.add_widget(name_label)
        title_container.add_widget(Widget())
        

        header.add_widget(Widget())
        header.add_widget(title_container)
        header.add_widget(Widget())
        self.add_widget(header)

        # 背景色
        with self.canvas.before:
            Color(0.925, 0.957, 0.910, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(self.rect, 'pos', i.pos))
        self.bind(size=lambda i, v: setattr(self.rect, 'size', i.size))

        # メッセージリスト
        self.scroll = ScrollView(size_hint=(1, 1))
        self.chat_list = GridLayout(cols=1, spacing=18, size_hint_y=None, padding=[10, 10])
        self.chat_list.bind(minimum_height=self.chat_list.setter('height'))
        self.scroll.add_widget(self.chat_list)
        self.add_widget(self.scroll)

        # 入力エリア
        input_layout = BoxLayout(size_hint_y=None, height=140, padding=[10, 5], spacing=10)
        with input_layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.input_rect = RoundedRectangle(pos=input_layout.pos, size=input_layout.size)
        input_layout.bind(pos=lambda i, v: setattr(self.input_rect, 'pos', i.pos))
        input_layout.bind(size=lambda i, v: setattr(self.input_rect, 'size', i.size))
        
        # メッセージ入力を縦方向中央に寄せるため固定高さにする
        self.message_input = TextInput(
            hint_text='メッセージ内容を入力',
            multiline=True,
            input_type='text',  # IME（日本語入力）を有効にするためテキスト入力モードに
            write_tab=False,
            font_size='16sp',
            font_name='NotoSansJP',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            size_hint_x=0.8,
            size_hint_y=None,
            height=140
        )
        # フォーカス時は IME を使って文字入力できるようにし、Enter は改行／IME確定に残す
        self.message_input.bind(focus=self.on_input_focus)
        
        send_button = ImageButton(
            source='img/send.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(120, 120)
        )
        send_button.bind(on_press=self.send_message)

        # 送信ボタンを縦中央に配置するコンテナ
        send_container = BoxLayout(orientation='vertical', size_hint=(None, 1), width=send_button.size[0])
        send_container.add_widget(Widget())
        send_container.add_widget(send_button)
        send_container.add_widget(Widget())

        input_layout.add_widget(self.message_input)
        input_layout.add_widget(send_container)
        self.add_widget(input_layout)

        # ハードキー（戻る）イベントを登録
        Window.bind(on_key_down=self.on_keyboard)
        self.load_messages()
        # 親ウィジェットが外れた（ウィジェットが破棄された/画面から離れた）ときに
        # イベントハンドラを解除するためのバインド
        def _on_parent_change(instance, parent):
            if parent is None:
                try:
                    Window.unbind(on_key_down=self.on_keyboard)
                except Exception:
                    pass

        self.bind(parent=_on_parent_change)

        # リアルタイム更新用のスケジューラー（3秒ごとにチェック）
        self.last_message_count = 0
        self.update_event = Clock.schedule_interval(self.check_new_messages, 3)
        

    def on_input_focus(self, instance, value):
        if value:
            from kivy.clock import Clock
            # 少し遅延を置いてスクロール（キーボード表示に追従）
            def scroll_to_bottom(dt):
                try:
                    self.scroll.scroll_y = 0
                except Exception:
                    pass
            Clock.schedule_once(scroll_to_bottom, 0.05)
            Clock.schedule_once(scroll_to_bottom, 0.25)

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        # Androidの戻るボタン処理
        if key == 27:  # ESC / Android戻るボタン
            self.go_back(None)
            return True  # イベントを消費
        
        # 日本語IME の確定（Enter）と送信操作が競合しないよう、
        # ここでは Ctrl+Enter (または Cmd+Enter) を送信ショートカットに割り当てる。
        # 普通の Enter は改行／IME確定に使用される。
        if key == 13 and ('ctrl' in modifier or 'meta' in modifier):
            if self.message_input.focus:
                self.send_message(None)
                return True
        return False

    def go_back(self, instance):
        # 戻る時はまずキーイベントを解除してから画面遷移
        try:
            Window.unbind(on_key_down=self.on_keyboard)
        except Exception:
            pass

        # チャット画面を離れる（戻る）ときは、
        # その会話を既読として現在時刻をチャット状態に保存する
        try:
            import os
            state_path = os.path.join(os.path.dirname(__file__), 'chat_state.json')
            state = {}
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            state[self.target_id] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"⚠️ 既読状態保存エラー (go_back): {e}")

        if self.app_instance:
            # 同じキーイベントが続けて別のハンドラに届くことを防ぐため、
            # 画面遷移をわずかに遅延させる（キーイベントのディスパッチが終わるまで待つ）
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.app_instance.back_to_list(), 0.06)

    def add_date_label(self, date_str):
        """日付ラベルを追加"""
        try:
            # 日付を見やすい形式に変換
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # 曜日を日本語で表示
            weekdays = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekdays[date_obj.weekday()]
            display_text = f"{date_obj.month}月{date_obj.day}日({weekday})"
        except:
            display_text = date_str
        
        # 日付ラベルのコンテナ（背景なし、中央表示）
        date_container = BoxLayout(
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 5]
        )

        date_label = Label(
            text=display_text,
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            font_name='NotoSansJP',
            size_hint=(None, None),
            height=30
        )
        date_label.bind(texture_size=date_label.setter('size'))

        # 中央に配置
        date_container.add_widget(Widget())
        date_container.add_widget(date_label)
        date_container.add_widget(Widget())

        self.chat_list.add_widget(date_container)

    def send_message(self, instance):
        message_text = self.message_input.text.strip()
        message_text = '\n'.join([message_text[i:i+10] for i in range(0, len(message_text), 10)])
        if not message_text:
            return
        
        try:
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M:%S')
            
            url = f"{SUPABASE_URL}/rest/v1/chat"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            data = {
                'userA_id': self.my_id,
                'userB_id': self.target_id,
                'log': message_text,
                'date': current_date,
                'time': current_time
            }
            
            res = requests.post(url, headers=headers, data=json.dumps(data))
            
            if res.status_code in (200, 201):
                # 最後のメッセージの日付をチェック
                if hasattr(self, 'last_message_date'):
                    if self.last_message_date != current_date:
                        self.add_date_label(current_date)
                else:
                    self.add_date_label(current_date)
                
                self.last_message_date = current_date
                response_data = res.json()
                new_message_id = response_data[0].get('chat_id') if response_data else None

                
                time_display = current_time[:5]
                bubble = MessageBubble(text=message_text, time=time_display, is_sent=True,message_id=new_message_id)
                self.chat_list.add_widget(bubble)
                
                self.message_input.text = ''
                
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
                
                # チャットリストが存在する場合はこの会話を先頭に移動
                try:
                    if self.app_instance and hasattr(self.app_instance, 'move_chat_to_top'):
                        self.app_instance.move_chat_to_top(self.target_id)
                except Exception:
                    pass

                print(f"メッセージ送信成功: {message_text}")
            else:
                print(f"⚠️ メッセージ送信失敗: {res.status_code} {res.text}")
                
        except Exception as e:
            print(f"❌ 送信エラー: {e}")
            import traceback
            traceback.print_exc()

    def load_messages(self, scroll_to_bottom=True):
        try:
            url = f"{SUPABASE_URL}/rest/v1/chat"
            params = {
                "select": "*",
                "or": f"(and(userA_id.eq.{self.my_id},userB_id.eq.{self.target_id}),and(userA_id.eq.{self.target_id},userB_id.eq.{self.my_id}))",
                "order": "date.asc,time.asc"
            }
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            res = requests.get(url, headers=headers, params=params)
            
            if res.status_code != 200:
                print(f"⚠️ メッセージ取得失敗: {res.status_code}")
                messages = []
            else:
                messages = res.json()
            
            if not messages:
                test_label = Label(
                    text='メッセージがありません',
                    color=(0, 0, 0, 1),
                    size_hint_y=None,
                    height=50,
                    font_name='NotoSansJP'
                )
                self.chat_list.add_widget(test_label)
            else:
                last_date = None
                
                for msg in messages:
                    current_date = msg.get('date', '')
                    
                    if current_date != last_date:
                        self.add_date_label(current_date)
                        last_date = current_date
                    
                    self.display_message(msg)
                
                # 最後の日付を保存
                self.last_message_date = last_date
                
                # メッセージ数を記録
                self.last_message_count = len(messages)
                
                if scroll_to_bottom:
                    def scroll_bottom(dt):
                        self.scroll.scroll_y = 0
                    Clock.schedule_once(scroll_bottom, 0.1)
                    
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()

    def display_message(self, msg):
        is_sent = (msg.get('userA_id') == self.my_id)
        text = msg.get('log', '')
        time_str = str(msg.get('time', ''))[:5]
        message_id = msg.get('chat_id')
        
        # 画像メッセージかどうかを判定
        is_image = text.startswith('[IMAGE]')
        if is_image:
            text = text.replace('[IMAGE]', '')  # プレフィックスを削除してURLのみにする

        bubble = MessageBubble(
            text=text,
            time=time_str,
            is_sent=is_sent,
            is_image=is_image,
            icon_url=None if is_sent else self.other_icon_url,
            message_id=message_id  
        )
        self.chat_list.add_widget(bubble)
        
    def delete_message(self, message_id, bubble_widget):
        try:
            url = f"{SUPABASE_URL}/rest/v1/chat"
            params = {"chat_id": f"eq.{message_id}"}
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            res = requests.delete(url, headers=headers, params=params)
            
            if res.status_code == 204:
                # バブルのインデックスを取得
                bubble_index = self.chat_list.children.index(bubble_widget)
                
                # UIからメッセージを削除
                self.chat_list.remove_widget(bubble_widget)
                
                # 削除後、前後のウィジェットをチェック
                # chat_list.childrenは逆順なので注意
                children = self.chat_list.children
                
                # 削除したメッセージの前（上）にある日付ラベルを探す
                date_label_to_remove = None
                if bubble_index < len(children):
                    # 削除した位置の次のウィジェット（画面上は上）
                    prev_widget = children[bubble_index]
                    # 日付ラベルかどうかチェック（BoxLayoutで、中にLabelが1つだけ）
                    if isinstance(prev_widget, BoxLayout) and len(prev_widget.children) == 3:
                        # 日付ラベルコンテナの構造: Widget, Label, Widget
                        middle_widget = prev_widget.children[1]
                        if isinstance(middle_widget, Label):
                            # この日付の下に他のメッセージがあるかチェック
                            has_messages_below = False
                            for i in range(bubble_index + 1, len(children)):
                                widget = children[i]
                                # MessageBubbleかチェック
                                if isinstance(widget, MessageBubble):
                                    has_messages_below = True
                                    break
                                # 別の日付ラベルに到達したら終了
                                if isinstance(widget, BoxLayout) and len(widget.children) == 3:
                                    break
                            
                            # この日付の下にメッセージがなければ削除
                            if not has_messages_below:
                                date_label_to_remove = prev_widget
                
                if date_label_to_remove:
                    self.chat_list.remove_widget(date_label_to_remove)
                    print(f"日付ラベルも削除しました")
                
                print(f"メッセージ削除成功: {message_id}")
            else:
                print(f"⚠️ メッセージ削除失敗: {res.status_code}")
                
        except Exception as e:
            print(f"❌ 削除エラー: {e}")
            import traceback
            traceback.print_exc()
            
    def check_new_messages(self, dt):
        """新しいメッセージがあるかチェック"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/chat"
            params = {
                "select": "chat_id",
                "or": f"(and(userA_id.eq.{self.my_id},userB_id.eq.{self.target_id}),and(userA_id.eq.{self.target_id},userB_id.eq.{self.my_id}))",
            }
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            res = requests.get(url, headers=headers, params=params)
            
            if res.status_code == 200:
                messages = res.json()
                current_count = len(messages)
                
                # メッセージ数が変わっていたら再読み込み
                if current_count != self.last_message_count:
                    # 現在のスクロール位置を保存
                    current_scroll = self.scroll.scroll_y
                    
                    # チャットリストをクリア
                    self.chat_list.clear_widgets()
                    
                    # メッセージを再読み込み(スクロールは現在位置を維持)
                    self.load_messages(scroll_to_bottom=False)
                    
                    # 新しいメッセージが相手から来た場合のみ最下部へスクロール
                    if current_count > self.last_message_count and current_scroll < 0.1:
                        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
                    else:
                        # それ以外は元の位置を維持
                        self.scroll.scroll_y = current_scroll
                    
                    # 既読状態を更新(チャット画面を開いている間は常に既読扱い)
                    try:
                        import os
                        state_path = os.path.join(os.path.dirname(__file__), 'chat_state.json')
                        state = {}
                        if os.path.exists(state_path):
                            with open(state_path, 'r', encoding='utf-8') as f:
                                state = json.load(f)
                        state[self.target_id] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                        with open(state_path, 'w', encoding='utf-8') as f:
                            json.dump(state, f)
                    except Exception as e:
                        print(f"⚠️ 既読状態保存エラー: {e}")
                        
        except Exception as e:
            print(f"⚠️ メッセージチェックエラー: {e}")