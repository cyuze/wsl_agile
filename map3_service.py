# -*- coding: utf-8 -*-
import json
import requests
from datetime import datetime

# ============================
# Android 権限
# ============================
try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False


def request_location_permissions():
    """Android の位置情報権限を要求"""
    if ANDROID:
        request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION])
    else:
        print("⚠️ Android以外なので権限要求スキップ")


# ============================
# Supabase 設定
# ============================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"  # ← map3.py と合わせてね


# ============================
# meeting 情報取得
# ============================
def get_active_meeting_info(user_mail):
    """
    自分が参加しているアクティブな meeting の情報を取得
    Returns:
        {
            "meeting_id": str,
            "location": (lat, lon),
            "place_name": str,
            "members": [user_mail1, user_mail2, ...]
        } or None
    """
    try:
        # Step 1: meeting_shares から meeting_id を取得
        url_shares = f"{SUPABASE_URL}/rest/v1/meeting_shares"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        params = {
            "select": "meeting_id",
            "user_mail": f"eq.{user_mail}",
            "status": "eq.true"
        }
        res = requests.get(url_shares, headers=headers, params=params)
        if res.status_code != 200 or not res.json():
            print("⚠️ meeting_shares にアクティブな共有が見つかりません")
            return None

        meeting_id = res.json()[0].get("meeting_id")

        # Step 2: meetings テーブルから場所情報を取得
        url_meetings = f"{SUPABASE_URL}/rest/v1/meetings"
        params_meeting = {
            "select": "location,place_name",
            "id": f"eq.{meeting_id}"
        }
        res2 = requests.get(url_meetings, headers=headers, params=params_meeting)
        if res2.status_code != 200 or not res2.json():
            print("⚠️ meetings テーブルから情報取得失敗")
            return None

        meeting_data = res2.json()[0]
        loc_str = meeting_data.get("location", "")
        lat, lon = map(float, loc_str.strip("{}").split(","))
        place_name = meeting_data.get("place_name", "")

        # Step 3: 同じ meeting_id を持つ user_mail を取得
        params_members = {
            "select": "user_mail",
            "meeting_id": f"eq.{meeting_id}"
        }
        res3 = requests.get(url_shares, headers=headers, params=params_members)
        members = [r.get("user_mail") for r in res3.json() if r.get("user_mail")]

        return {
            "meeting_id": meeting_id,
            "location": (lat, lon),
            "place_name": place_name,
            "members": members
        }

    except Exception as e:
        print(f"❌ get_active_meeting_info error: {e}")
        return None


# ============================
# MainScreen のロジック
# ============================
class MainScreenLogic:
    def __init__(self, screen):
        self.screen = screen
        self.app = screen.app_instance

    # ------------------------
    # 待ち合わせ終了
    # ------------------------
    def on_end_meeting(self, instance):
        """待ち合わせ終了ボタン - 現在案内している場所のIDのmeetingとmeeting_sharesのstatusをfalseにしてmap.pyへ戻る"""
        print("🛑 待ち合わせ終了")
        
        try:
            # meeting_status_check_eventをキャンセル（重要：2回目以降の自動化に必須）
            if hasattr(self.screen, 'meeting_status_check_event') and self.screen.meeting_status_check_event:
                self.screen.meeting_status_check_event.cancel()
                print("✅ meeting_status_check_eventをキャンセルしました")
            
            # screenからmeeting_idを取得
            meeting_id = getattr(self.screen, 'meeting_id', None)
            
            if not meeting_id:
                print("⚠️ meeting_id が見つかりません - users.jsonから取得を試みます")
                # users.jsonからメールアドレスを取得
                with open("users.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                user_mail = data[0].get("user_mail") if isinstance(data, list) else data.get("user_mail")
                
                if user_mail:
                    # meeting_sharesから自分のアクティブなmeeting_idを取得
                    url_shares = f"{SUPABASE_URL}/rest/v1/meeting_shares"
                    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                    params = {
                        "select": "meeting_id",
                        "user_mail": f"eq.{user_mail}",
                        "status": "eq.true"
                    }
                    
                    res = requests.get(url_shares, headers=headers, params=params)
                    if res.status_code == 200 and res.json():
                        meeting_id = res.json()[0].get("meeting_id")
                        print(f"📍 meeting_sharesから取得したmeeting_id: {meeting_id}")
            
            if meeting_id:
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
                
                print(f"📍 処理対象のmeeting_id（場所のID）: {meeting_id}")
                
                # Step 1: meeting_sharesで該当meeting_idのすべてのレコードのstatusをfalseに更新
                update_data = {"status": False}
                url_shares = f"{SUPABASE_URL}/rest/v1/meeting_shares"
                params_update = {"meeting_id": f"eq.{meeting_id}"}
                
                res_shares = requests.patch(url_shares, headers=headers, params=params_update, data=json.dumps(update_data))
                if res_shares.status_code in (200, 204):
                    print(f"✅ meeting_shares のステータスをfalseに更新しました（meeting_id: {meeting_id}）")
                else:
                    print(f"⚠️ meeting_shares 更新失敗: {res_shares.status_code}")
                
                # Step 2: meetingsテーブルでも該当meeting_idのstatusをfalseに更新
                url_meetings = f"{SUPABASE_URL}/rest/v1/meetings"
                params_meetings = {"id": f"eq.{meeting_id}"}
                
                res_meetings = requests.patch(url_meetings, headers=headers, params=params_meetings, data=json.dumps(update_data))
                if res_meetings.status_code in (200, 204):
                    print(f"✅ meetings のステータスをfalseに更新しました（meeting_id: {meeting_id}）")
                else:
                    print(f"⚠️ meetings 更新失敗: {res_meetings.status_code}")
            else:
                print("⚠️ meeting_id が取得できませんでした")
            
        except Exception as e:
            print(f"❌ on_end_meeting error: {e}")
            import traceback
            traceback.print_exc()
        
        # map.pyへ戻る
        if self.app:
            from kivy.uix.screenmanager import ScreenManager
            if isinstance(self.app.root, ScreenManager):
                print("🔄 ScreenManager経由でmap画面へ遷移")
                
                # mapスクリーンが存在するか確認
                if self.app.root.has_screen("map"):
                    # mapスクリーンの定期処理を再開（重要：2回目以降の自動化に必須）
                    if hasattr(self.app, 'main_screen') and hasattr(self.app.main_screen, 'resume_updates'):
                        self.app.main_screen.resume_updates()
                        print("📍 map.pyの定期処理を再開しました")
                    self.app.root.current = "map"
                else:
                    # mapスクリーンがない場合は作成
                    print("⚠️ mapスクリーンが存在しないため作成します")
                    from kivy.uix.screenmanager import Screen
                    from map import MainScreen as MapMainScreen
                    
                    class MapScreen(Screen):
                        def __init__(self, app_inst, **kwargs):
                            super().__init__(name="map", **kwargs)
                            app_inst.main_screen = MapMainScreen(
                                app_instance=app_inst, 
                                current_user=app_inst.current_user
                            )
                            self.add_widget(app_inst.main_screen)
                    
                    map_screen = MapScreen(app_inst=self.app)
                    self.app.root.add_widget(map_screen)
                    self.app.root.current = "map"
            else:
                print("🔄 back_to_map()でmap画面へ遷移")
                self.app.back_to_map()

    # ------------------------
    # 友達ボタン
    # ------------------------
    def on_friend_button(self, instance):
        if self.app:
            # 前の画面をmap3として記録
            self.app.previous_screen = "map3"
            self.app.open_friend_addition()

    # ------------------------
    # チャットボタン
    # ------------------------
    def on_chat_button(self, instance):
        if self.app:
            # 前の画面をmap3として記録
            self.app.previous_screen = "map3"
            self.app.open_chat_list()

    # ------------------------
    # 設定ボタン
    # ------------------------
    def on_settings_button(self, instance):
        if self.app:
            # 前の画面をmap3として記録
            self.app.previous_screen = "map3"
            self.app.open_settings()