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
SUPABASE_KEY = "YOUR_KEY"  # ← map3.py と合わせてね


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
        print("🛑 待ち合わせ終了")
        if self.app:
            self.app.back_to_map()

    # ------------------------
    # 友達ボタン
    # ------------------------
    def on_friend_button(self, instance):
        if self.app:
            self.app.open_friend_addition()

    # ------------------------
    # チャットボタン
    # ------------------------
    def on_chat_button(self, instance):
        if self.app:
            self.app.open_chat_list()

    # ------------------------
    # 設定ボタン
    # ------------------------
    def on_settings_button(self, instance):
        if self.app:
            self.app.open_settings()