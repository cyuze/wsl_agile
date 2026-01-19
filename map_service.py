import requests
import json
from datetime import datetime

# ===============================================================
# Supabase 設定 (サービス層)
# ===============================================================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"
MY_ID = "cb3cce5a-3ec7-4837-b998-fd9d5446f04a"


def fetch_friends(user_id):
    url = f"{SUPABASE_URL}/rest/v1/friend"
    params = {"select": "send_user,recive_user,permission",
              "or": f"(send_user.eq.{user_id},recive_user.eq.{user_id})"}
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            return []
        friends = []
        for r in res.json():
            if not r.get("permission"):
                continue
            fid = r["recive_user"] if r["send_user"] == user_id else r["send_user"]
            if fid != user_id:
                friends.append(fid)
        return friends
    except Exception as e:
        print("⚠️ map_service.fetch_friends:", e)
        return []





def fetch_friend_icon(friend_id):
    url = f"{SUPABASE_URL}/rest/v1/users?select=icon_url&user_id=eq.{friend_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data:
            return data[0].get("icon_url")
    except Exception as e:
        print("⚠️ map_service.fetch_friend_icon:", e)
    return None


def get_friend_mail(friend_id):
    """friend_id から friend_mail を取得
    
    Args:
        friend_id: ユーザーID
    
    Returns:
        メールアドレス、または None
    """
    url = f"{SUPABASE_URL}/rest/v1/users?select=mail&user_id=eq.{friend_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data:
            return data[0].get("mail")
    except Exception as e:
        print("⚠️ map_service.get_friend_mail:", e)
    return None


def fetch_friend_location(friend_mail):
    """location テーブルから友人のメールアドレス経由で位置情報を取得
    
    Args:
        friend_mail: 友人のメールアドレス
    
    Returns:
        (lat, lon) のタプル、または None
    """
    url = f"{SUPABASE_URL}/rest/v1/location?select=location&mail=eq.{friend_mail}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return None
        data = res.json()
        if not data:
            return None
        loc_str = data[0].get("location")
        if not loc_str:
            return None
        # "{lat,lon}" 形式をパース
        lat, lon = map(float, loc_str.strip("{}").split(","))
        return lat, lon
    except Exception as e:
        print("⚠️ map_service.fetch_friend_location:", e)
    return None


def save_my_location(gps):
    """users.json の user_mail と渡された gps 情報で
    Supabase の `location` テーブルに upsert（登録/更新）します。

    - `gps` は (lat, lon) のタプル/リスト、もしくは 'lat,lon' 文字列を受け取ります。
    - `location` カラムには文字列の形式で "{緯度,経度}" を保存します。
    - `update_at` は UTC の ISO 形式で保存します。
    """
    try:
        # users.json からメールを取得
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # data がリスト形式の場合は最初の要素を取得
        if isinstance(data, list):
            if len(data) == 0:
                print("⚠️ save_my_location: users.json is empty list")
                return False
            data = data[0]
        
        mail = data.get("user_mail") or data.get("mail")
        if not mail:
            print("⚠️ save_my_location: user_mail not found in users.json")
            return False

        # GPS の正規化
        if isinstance(gps, (list, tuple)):
            lat, lon = float(gps[0]), float(gps[1])
        elif isinstance(gps, str):
            parts = gps.split(",")
            if len(parts) != 2:
                print("⚠️ save_my_location: invalid gps string")
                return False
            lat, lon = float(parts[0]), float(parts[1])
        else:
            print("⚠️ save_my_location: unsupported gps format")
            return False

        loc_str = "{" + f"{lat},{lon}" + "}"
        payload = {
            "mail": mail,
            "location": loc_str,
            "update_at": datetime.utcnow().isoformat() + "Z",
        }

        url = f"{SUPABASE_URL}/rest/v1/location"
        headers_base = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

        # まず PATCH で既存行を更新してみる（mail が一致する行）
        try:
            pres = requests.patch(url, headers=headers_base, params={"mail": f"eq.{mail}"}, data=json.dumps({"location": loc_str, "update_at": datetime.utcnow().isoformat() + "Z"}))
            if pres.status_code in (200, 204):
                return True
        except Exception:
            pass

        # PATCHで更新できなければ、POSTで upsert を試す（Prefer ヘッダで merge-duplicates を指定）
        headers_insert = headers_base.copy()
        headers_insert["Prefer"] = "resolution=merge-duplicates"
        insert_url = f"{url}?on_conflict=mail"
        try:
            ires = requests.post(insert_url, headers=headers_insert, data=json.dumps(payload))
            if ires.status_code in (200, 201, 204):
                return True
            else:
                print(f"⚠️ save_my_location: supabase returned {ires.status_code} {ires.text}")
        except Exception as e:
            print("⚠️ save_my_location: post error", e)
    except Exception as e:
        print("⚠️ map_service.save_my_location:", e)
    return False
