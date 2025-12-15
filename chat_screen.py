from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.image import AsyncImage
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color, RoundedRectangle, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.core.text import LabelBase
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
import requests
import json
import os
from datetime import datetime
from kivy.core.window import Window
from kivy.clock import Clock


# personal_chat_screenをインポート
from personal_chat_screen import ChatScreen

# -----------------------------
# 日本語フォントの登録
LabelBase.register(name='NotoSansJP',
                   fn_regular='NotoSansJP-Regular.ttf')

# -----------------------------
# Supabase 設定
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"

MY_USER_ID = "cb3cce5a-3ec7-4837-b998-fd9d5446f04a"

# -----------------------------
# 完全版 CircularImage(はみ出しゼロ&中央表示)
class CircularImage(StencilView):
    def __init__(self, source, size=(60, 60), **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = size
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

        # サイズや位置が変わったら更新
        self.bind(pos=self.update_mask, size=self.update_mask)

    def update_mask(self, *args):
        # マスク(丸)更新
        self.mask.pos = self.pos
        self.mask.size = self.size

        # 画像をちょうどフィットさせる(丸内部にぴったり)
        self.image.pos = self.pos
        self.image.size = self.size


# -----------------------------
class ChatListItem(ButtonBehavior, BoxLayout):
    def __init__(self, name, message, icon_url=None, unread_count=0, other_user_id=None, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 80
        self.padding = [15, 10, 15, 10]
        self.spacing = 15
        self.other_user_id = other_user_id
        self.app_instance = app_instance
        self.user_name = name
        self.last_message = message

        # 背景色
        with self.canvas.before:
            Color(0.925, 0.957, 0.91, 1)  # ECF4E8
            self.rect = RoundedRectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._update_rect, size=self._update_rect)
            
            with self.canvas.after:
                Color(0, 0, 0, 1)  # 黒
                self.bottom_line = RoundedRectangle(
                    pos=(self.x, self.y),      # 下側
                    size=(self.width, 2)       # 横幅いっぱい、高さ2px
                )

        # 位置とサイズを追従させる
        self.bind(
            pos=lambda *_: setattr(self.bottom_line, "pos", (self.x, self.y)),
            size=lambda *_: setattr(self.bottom_line, "size", (self.width, 2))
        )

        # -------- アバター表示(全部統一して丸表示) --------
        avatar_widget = CircularImage(source=icon_url if icon_url else "img/default.png", size=(112, 112))
        avatar_layout = BoxLayout(orientation='vertical', size_hint=(None, 1), width=avatar_widget.size[0])
        avatar_layout.add_widget(Widget())
        avatar_layout.add_widget(avatar_widget)
        avatar_layout.add_widget(Widget())

        # -------- テキスト --------
        text_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_x=1)

        name_label = Label(
            text=name,
            size_hint_y=None,
            color=(0, 0, 0, 1),
            font_size='16sp',
            font_name='NotoSansJP',
            halign='left',
            valign='middle'
        )
        name_label.text_size = (0, None)
        name_label.bind(width=lambda inst, w: inst.setter('text_size')(inst, (w, None)))
        name_label.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))

        message_label = Label(
            text=message,
            size_hint_y=None,
            color=(0.4, 0.4, 0.4, 1),
            font_size='14sp',
            font_name='NotoSansJP',
            halign='left',
            valign='middle'
        )
        message_label.text_size = (0, None)
        message_label.bind(width=lambda inst, w: inst.setter('text_size')(inst, (w, None)))
        message_label.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))

        text_layout.add_widget(name_label)
        text_layout.add_widget(message_label)

        # -------- 未読表示: 件数ラベル + 大きめの mail アイコン --------
        if unread_count and unread_count > 0:
            mail_path = os.path.join(os.path.dirname(__file__), 'img', 'mail.png')
            if os.path.exists(mail_path):
                mail_icon = Image(source=mail_path, size_hint=(None, None), size=(72, 72), allow_stretch=True, keep_ratio=True)
            else:
                mail_icon = Image(source='img/send.png', size_hint=(None, None), size=(72, 72), allow_stretch=True, keep_ratio=True)

            count_label = Label(
                text=f'新着{unread_count}件',
                font_size='14sp',
                font_name='NotoSansJP',
                color=(0, 0, 0, 1),
                size_hint=(None, None),
                halign='left',
                valign='middle'
            )
            try:
                count_label.texture_update()
                tw, th = count_label.texture_size
                count_label.size = (tw + 8, th)
            except Exception:
                count_label.size = (120, 24)

            right_h = BoxLayout(orientation='horizontal', size_hint=(None, 1), spacing=12)
            right_h.width = (count_label.width + 12 + 72)
            lbl_container = BoxLayout(orientation='vertical', size_hint=(None, 1), width=count_label.width)
            lbl_container.add_widget(Widget())
            lbl_container.add_widget(count_label)
            lbl_container.add_widget(Widget())

            icon_container = BoxLayout(orientation='vertical', size_hint=(None, 1), width=mail_icon.size[0] + 6)
            icon_container.add_widget(Widget())
            icon_container.add_widget(mail_icon)
            icon_container.add_widget(Widget())

            right_h.add_widget(lbl_container)
            right_h.add_widget(icon_container)
            right_widget = right_h
        else:
            right_widget = Widget()

        self.add_widget(avatar_layout)
        self.add_widget(text_layout)
        self.add_widget(right_widget)

        def _update_item_height(*args):
            name_h = getattr(name_label, 'height', 0) or 0
            msg_h = getattr(message_label, 'height', 0) or 0

            labels_total = name_h + msg_h
            total_padding = (self.padding[1] if len(self.padding) > 1 else 0) + (self.padding[3] if len(self.padding) > 3 else 0)
            spacing = text_layout.spacing if hasattr(text_layout, 'spacing') else 0
            required_height = labels_total + total_padding + spacing

            avatar_h = avatar_widget.size[1] if 'avatar_widget' in locals() and hasattr(avatar_widget, 'size') else (avatar_layout.size[1] if hasattr(avatar_layout, 'size') else 0)
            new_height = max(avatar_h + total_padding, required_height, 60)

            new_height = int(new_height + 8)
            if self.height != new_height:
                self.height = new_height

        name_label.bind(texture_size=lambda *_: _update_item_height())
        message_label.bind(texture_size=lambda *_: _update_item_height())
        avatar_layout.bind(size=lambda *_: _update_item_height())
        _update_item_height()

    def on_press(self):
        if self.app_instance and self.other_user_id:
            try:
                app = self.app_instance
                state_path = os.path.join(os.path.dirname(__file__), 'chat_state.json')
                state = {}
                if os.path.exists(state_path):
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                state[self.other_user_id] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f)
            except Exception:
                pass

            self.app_instance.open_chat(MY_USER_ID, self.other_user_id)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def matches_search(self, query):
        query = query.lower()
        return (query in self.user_name.lower()) or (query in self.last_message.lower())


# -----------------------------
class MainLayout(BoxLayout):
    def __init__(self, app_instance=None, **kwargs):
        super().__init__(**kwargs)
        
        # 🔥 戻るボタンのキーボードイベントをバインド
        self._keyboard_bind = Window.bind(on_keyboard=self.on_back_button)

        # 親が外れたときにキーバインドを解除する
        def _on_parent_change(instance, parent):
            if parent is None:
                try:
                    Window.unbind(on_keyboard=self.on_back_button)
                except Exception:
                    pass

        self.bind(parent=_on_parent_change)
        
        with self.canvas.before:
            Color(0.925, 0.957, 0.91, 1)  # ECF4E8
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size)

        self.bind(
            pos=lambda *_: setattr(self.bg_rect, "pos", self.pos),
            size=lambda *_: setattr(self.bg_rect, "size", self.size)
        )

        self.orientation = 'vertical'
        self.app_instance = app_instance
        self.all_chat_items = []
        self.state_path = os.path.join(os.path.dirname(__file__), 'chat_state.json')
        self.chat_state = {}
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    self.chat_state = json.load(f)
        except Exception:
            self.chat_state = {}

        # -------- 検索バー --------
        search_layout = BoxLayout(
            size_hint_y=None,
            height=140,
            padding=[15, 14, 15, 14]
        )
        with search_layout.canvas.after:
            Color(0, 0, 0, 1)
            self.search_line = RoundedRectangle(pos=(search_layout.x, search_layout.y), size=(search_layout.width, 2))

        search_layout.bind(
            pos=lambda inst, val: setattr(self.search_line, "pos", (inst.x, inst.y)),
            size=lambda inst, val: setattr(self.search_line, "size", (inst.width, 2))
        )
        
        with search_layout.canvas.before:
            Color(0.796, 0.953, 0.733, 1)  # CBF3BB
            self.search_rect = RoundedRectangle(pos=search_layout.pos, size=search_layout.size)
        search_layout.bind(pos=self._update_search_rect, size=self._update_search_rect)

        search_box = BoxLayout(spacing=10)

        search_icon = Image(
            source='img/search.png',
            size_hint=(None, None),
            size=(70, 70),
            allow_stretch=True,
            keep_ratio=True,
            pos_hint={'center_y': 0.5}
        )

        self.search_input = TextInput(
            hint_text='検索',
            size_hint_x=1,
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            multiline=False,
            font_size='16sp',
            font_name='NotoSansJP',
            input_type='text',     
        )

        def adjust_padding(instance, value):
            instance.padding_y = (instance.height - instance.line_height) / 2

        self.search_input.bind(size=adjust_padding)
        self.search_input.bind(text=self.on_search_text)

        search_box.add_widget(search_icon)
        search_box.add_widget(self.search_input)
        search_layout.add_widget(search_box)

        self.update_event = Clock.schedule_interval(self.check_for_updates, 5)
        
        scroll = ScrollView(size_hint=(1, 1))
        
        def disable_scroll_on_focus(instance, value):
            if value:
                scroll.scroll_y = 1
        self.search_input.bind(focus=disable_scroll_on_focus)
        
        self.chat_list = GridLayout(cols=1, spacing=1, size_hint_y=None)
        self.chat_list.bind(minimum_height=self.chat_list.setter('height'))
        scroll.add_widget(self.chat_list)

        self.add_widget(search_layout)
        self.add_widget(scroll)

        self.load_chats()

    # 🔥 Androidの戻るボタン処理を追加
    def on_back_button(self, window, key, *args):
        """Androidの戻るボタンでmap画面に戻る"""
        if key == 27:  # ESC / Android戻るボタン
            if self.app_instance:
                self.app_instance.open_map_screen()
            return True  # イベントを消費
        return False
    
    def __del__(self):
        """ウィジェットが削除される時にイベントをアンバインド"""
        try:
            Window.unbind(on_keyboard=self.on_back_button)
        except:
            pass

    def _update_search_rect(self, instance, value):
        self.search_rect.pos = instance.pos
        self.search_rect.size = instance.size

    def on_search_text(self, instance, value):
        query = value.strip()
        self.chat_list.clear_widgets()

        if not query:
            for item in self.all_chat_items:
                self.chat_list.add_widget(item)
        else:
            for item in self.all_chat_items:
                if item.matches_search(query):
                    self.chat_list.add_widget(item)

            if len(self.chat_list.children) == 0:
                no_result = Label(
                    text='検索結果がありません',
                    color=(0.5, 0.5, 0.5, 1),
                    font_name='NotoSansJP',
                    size_hint_y=None,
                    height=100
                )
                self.chat_list.add_widget(no_result)

    def load_chats(self):
        url = f"{SUPABASE_URL}/rest/v1/friend"
        params = {
            "select": "send_user,recive_user,permission",
            "or": f"(send_user.eq.{MY_USER_ID},recive_user.eq.{MY_USER_ID})",
            "permission": "eq.true"
        }
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code != 200:
                print("⚠️ friend取得失敗:", res.status_code, res.text)
                friends = []
            else:
                friends = res.json()
        except Exception as e:
            print("❌ friend取得エラー:", e)
            friends = []

        if not friends:
            no_friend_label = Label(
                text='フレンドがいません',
                color=(0.5, 0.5, 0.5, 1),
                font_name='NotoSansJP',
                size_hint_y=None,
                height=100
            )
            self.chat_list.add_widget(no_friend_label)
            return

        friend_ids = [
            friend['recive_user'] if friend['send_user'] == MY_USER_ID else friend['send_user']
            for friend in friends
        ]

        temp_items = []
        for friend_id in friend_ids:
            user_url = f"{SUPABASE_URL}/rest/v1/users"
            user_params = {
                "select": "user_name,icon_url",
                "user_id": f"eq.{friend_id}"
            }
            
            try:
                user_res = requests.get(user_url, headers=headers, params=user_params)
                if user_res.status_code != 200:
                    continue
                
                user_data = user_res.json()
                if not user_data:
                    continue

                friend_name = user_data[0]['user_name']
                icon_url = user_data[0].get('icon_url')
            except Exception as e:
                print(f"❌ ユーザー情報取得エラー: {e}")
                continue

            chat_url = f"{SUPABASE_URL}/rest/v1/chat"
            chat_params = {
                "select": "*",
                "or": f"(and(userA_id.eq.{MY_USER_ID},userB_id.eq.{friend_id}),and(userA_id.eq.{friend_id},userB_id.eq.{MY_USER_ID}))",
                "order": "date.desc,time.desc",
                "limit": "1"
            }
            
            last_message = f"{friend_name}と会話をする"
            last_dt = None
            last_sender = None
            try:
                chat_res = requests.get(chat_url, headers=headers, params=chat_params)
                if chat_res.status_code == 200:
                    messages = chat_res.json()
                    if messages:
                        msg = messages[0]
                        last_message = msg.get('log', last_message)
                        d = msg.get('date') or ''
                        t = msg.get('time') or ''
                        try:
                            last_dt = datetime.strptime(f"{d}T{t}", '%Y-%m-%dT%H:%M:%S')
                        except Exception:
                            last_dt = None
                        last_sender = msg.get('userA_id') or msg.get('user_id') or None
            except Exception as e:
                print(f"❌ メッセージ取得エラー: {e}")

            temp_items.append((friend_id, friend_name, icon_url, last_message, last_dt, last_sender))

        temp_items.sort(key=lambda x: x[4] or datetime.min, reverse=True)

        self.all_chat_items = []
        for friend_id, friend_name, icon_url, last_message, last_dt, last_sender in temp_items:
            unread_count = 0
            try:
                saved = self.chat_state.get(friend_id)
                if saved:
                    saved_dt = datetime.strptime(saved, '%Y-%m-%dT%H:%M:%S')
                else:
                    saved_dt = datetime.min

                count_url = f"{SUPABASE_URL}/rest/v1/chat"
                count_params = {
                    "select": "date,time,userA_id",
                    "or": f"(and(userA_id.eq.{MY_USER_ID},userB_id.eq.{friend_id}),and(userA_id.eq.{friend_id},userB_id.eq.{MY_USER_ID}))",
                    "order": "date.desc,time.desc",
                    "limit": "200"
                }
                try:
                    count_res = requests.get(count_url, headers=headers, params=count_params)
                    if count_res.status_code == 200:
                        msgs = count_res.json()
                        for m in msgs:
                            d = m.get('date') or ''
                            t = m.get('time') or ''
                            try:
                                msg_dt = datetime.strptime(f"{d}T{t}", '%Y-%m-%dT%H:%M:%S')
                            except Exception:
                                msg_dt = None
                            sender = m.get('userA_id') or m.get('user_id') or None
                            if msg_dt and sender and sender != MY_USER_ID and msg_dt > saved_dt:
                                unread_count += 1
                except Exception:
                    unread_count = 0
            except Exception:
                unread_count = 0

            chat_item = ChatListItem(
                friend_name,
                last_message,
                icon_url=icon_url,
                unread_count=unread_count,
                other_user_id=friend_id,
                app_instance=self.app_instance
            )
            self.all_chat_items.append(chat_item)

        self.chat_list.clear_widgets()
        for item in self.all_chat_items:
            self.chat_list.add_widget(item)
            
    def check_for_updates(self, dt):
        """定期的にチャットリストを更新"""
        try:
            if self.search_input.text.strip():
                return
            
            self.load_chats()
        except Exception as e:
            print(f"⚠️ 更新エラー: {e}")


