import requests
import json
from datetime import datetime

# ===============================================================
# Supabase 設定 (サービス層)
# ===============================================================
SUPABASE_URL = "https://impklpvfmyvydnoayhfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImltcGtscHZmbXl2eWRub2F5aGZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTcyNzUsImV4cCI6MjA3Nzk3MzI3NX0.-z8QMhOvgRotNl7nFGm_ijj1SQIuhVuCMoa9_UXKci4"
MY_ID = "cb3cce5a-3ec7-4837-b998-fd9d5446f04a"


def initialize_user_location(user_mail, initial_lat=None, initial_lon=None):
    """ログインしたユーザーの位置情報を location テーブルに初期化
    
    Args:
        user_mail: ユーザーのメールアドレス
        initial_lat: 初期緯度（デフォルト：None。Noneの場合は既存の位置情報を保持）
        initial_lon: 初期経度
    
    Returns:
        True: 初期化成功または既存データ保持
        False: エラー発生
    """
    try:
        # 既存のレコードを確認（重要：既存の位置情報を絶対に上書きしない）
        url = f"{SUPABASE_URL}/rest/v1/location"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        params = {"select": "location", "mail": f"eq.{user_mail}"}
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200 and res.json():
            # 既存の位置情報がある場合は、絶対に上書きしない
            existing_location = res.json()[0].get("location")
            print(f"✅ map_service.initialize_user_location: {user_mail} の位置情報は既存の値を保持 {existing_location}")
            return True
        
        # 既存の位置情報がない場合のみ、新規作成を試みる
        if initial_lat is None or initial_lon is None:
            # GPS待ちモード：初期値がないため、位置情報がGPSで取得されるまで待つ
            print(f"⚠️ map_service.initialize_user_location: {user_mail} の位置情報はGPS取得待ち（初期値なし）")
            return False
        
        # 初期座標が指定されている場合のみ作成
        loc_str = "{" + f"{initial_lat},{initial_lon}" + "}"
        payload = {
            "mail": user_mail,
            "location": loc_str,
            "update_at": datetime.utcnow().isoformat() + "Z",
        }

        headers_insert = headers.copy()
        headers_insert["Content-Type"] = "application/json"
        headers_insert["Prefer"] = "resolution=merge-duplicates"
        insert_url = f"{url}?on_conflict=mail"
        
        res = requests.post(insert_url, headers=headers_insert, data=json.dumps(payload))
        if res.status_code in (200, 201, 204):
            print(f"✅ map_service.initialize_user_location: {user_mail} の位置情報を初期化 ({initial_lat}, {initial_lon})")
            return True
        else:
            print(f"⚠️ map_service.initialize_user_location: POST failed {res.status_code} {res.text}")
            return False
    except Exception as e:
        print(f"⚠️ map_service.initialize_user_location: {e}")
        return False


def ensure_user_registered(user_mail):
    """user_mail が users テーブルに存在しない場合は登録する
    
    Args:
        user_mail: ユーザーのメールアドレス
    
    Returns:
        True: 登録済みまたは新規登録成功
        False: エラー発生
    """
    url = f"{SUPABASE_URL}/rest/v1/users"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    
    try:
        # まず、このメールアドレスが既に存在するかチェック
        params = {"select": "user_mail", "user_mail": f"eq.{user_mail}"}
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200 and res.json():
            # 既に登録済み
            return True
        
        # 未登録の場合、新規作成
        headers["Content-Type"] = "application/json"
        payload = {
            "user_mail": user_mail,
            "user_name": user_mail,  # デフォルトではメールアドレスを名前に設定
            "icon_url": ""  # デフォルト画像なし
        }
        
        res = requests.post(url, headers=headers, data=json.dumps(payload))
        if res.status_code in (200, 201):
            print(f"✅ map_service.ensure_user_registered: {user_mail} を登録")
            return True
        else:
            print(f"⚠️ map_service.ensure_user_registered: POST failed {res.status_code} {res.text}")
            return False
    except Exception as e:
        print(f"⚠️ map_service.ensure_user_registered: {e}")
        return False


def get_user_id_by_mail(user_mail):
    """メールアドレスからuser_idを取得
    
    Args:
        user_mail: ユーザーのメールアドレス
    
    Returns:
        user_id文字列、またはNone
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/users"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        params = {"select": "user_id", "user_mail": f"eq.{user_mail}"}
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()
            if data:
                return data[0].get("user_id")
    except Exception as e:
        print(f"⚠️ map_service.get_user_id_by_mail: {e}")
    return None


def fetch_friends_by_mail(user_mail):
    """メールアドレスから友人を取得（send_user OR recive_user = 自分のメールかつpermission=trueの相手を取得）
    
    Args:
        user_mail: ユーザーのメールアドレス
    
    Returns:
        友人のuser_idリスト
    """
    url = f"{SUPABASE_URL}/rest/v1/friend"
    # (send_user = 自分のメール OR recive_user = 自分のメール) かつ permission = true のレコードを取得
    params = {"select": "send_user,recive_user,permission",
              "or": f"(send_user.eq.{user_mail},recive_user.eq.{user_mail})",
              "permission": "eq.true"}
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            print(f"⚠️ map_service.fetch_friends_by_mail: GET failed {res.status_code}")
            return []
        
        friends = []
        data = res.json()
        print(f"🔍 DEBUG map_service.fetch_friends_by_mail: Got {len(data)} friend records for {user_mail}")
        
        for r in data:
            send_user = r.get("send_user")
            recive_user = r.get("recive_user")
            
            # send_user が自分なら、recive_user を友人として追加
            if send_user == user_mail and recive_user != user_mail:
                friends.append(recive_user)
                print(f"🔍 DEBUG map_service.fetch_friends_by_mail: Added friend (as reciver) {recive_user}")
            # recive_user が自分なら、send_user を友人として追加
            elif recive_user == user_mail and send_user != user_mail:
                friends.append(send_user)
                print(f"🔍 DEBUG map_service.fetch_friends_by_mail: Added friend (as sender) {send_user}")
        
        return friends
    except Exception as e:
        print(f"⚠️ map_service.fetch_friends_by_mail: {e}")
        return []


def fetch_friends(user_id):
    """user_idから友人を取得（send_user OR recive_user = 自分かつpermission=trueの相手を取得）
    
    Args:
        user_id: ユーザーのID
    
    Returns:
        友人のuser_idリスト
    """
    url = f"{SUPABASE_URL}/rest/v1/friend"
    # (send_user = 自分 OR recive_user = 自分) かつ permission = true のレコードを取得
    params = {"select": "send_user,recive_user,permission",
              "or": f"(send_user.eq.{user_id},recive_user.eq.{user_id})",
              "permission": "eq.true"}
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            print(f"⚠️ map_service.fetch_friends: GET failed {res.status_code}")
            return []
        
        friends = []
        data = res.json()
        print(f"🔍 DEBUG map_service.fetch_friends: Got {len(data)} friend records")
        
        for r in data:
            send_user = r.get("send_user")
            recive_user = r.get("recive_user")
            
            # send_user が自分なら、recive_user を友人として追加
            if send_user == user_id and recive_user != user_id:
                friends.append(recive_user)
                print(f"🔍 DEBUG map_service.fetch_friends: Added friend (as reciver) {recive_user}")
            # recive_user が自分なら、send_user を友人として追加
            elif recive_user == user_id and send_user != user_id:
                friends.append(send_user)
                print(f"🔍 DEBUG map_service.fetch_friends: Added friend (as sender) {send_user}")
        
        return friends
    except Exception as e:
        print("⚠️ map_service.fetch_friends:", e)
        return []


def fetch_friend_icon(friend_mail):
    """友人のメールアドレスからアイコンURLを取得
    
    Args:
        friend_mail: 友人のメールアドレス（user_id または user_mail）
    
    Returns:
        icon_url文字列、またはNone
    """
    # まず、user_mail として検索
    url = f"{SUPABASE_URL}/rest/v1/users?select=icon_url&user_mail=eq.{friend_mail}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        print(f"🔍 fetch_friend_icon({friend_mail}): response = {data}")
        if data:
            icon_url = data[0].get("icon_url")
            print(f"📷 Found icon_url for {friend_mail}: {icon_url}")
            return icon_url
        else:
            # user_mail で見つからない場合、user_id として検索
            url = f"{SUPABASE_URL}/rest/v1/users?select=icon_url&user_id=eq.{friend_mail}"
            res = requests.get(url, headers=headers)
            data = res.json()
            print(f"🔍 fetch_friend_icon({friend_mail}) as user_id: response = {data}")
            if data:
                icon_url = data[0].get("icon_url")
                print(f"📷 Found icon_url for {friend_mail}: {icon_url}")
                return icon_url
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
    url = f"{SUPABASE_URL}/rest/v1/users?select=user_mail&user_id=eq.{friend_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if data:
            return data[0].get("user_mail")
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
            print(f"⚠️ map_service.fetch_friend_location: GET failed {res.status_code} for {friend_mail}")
            return None
        data = res.json()
        if not data:
            print(f"⚠️ map_service.fetch_friend_location: No location data for {friend_mail}")
            return None
        loc_str = data[0].get("location")
        if not loc_str:
            print(f"⚠️ map_service.fetch_friend_location: Empty location string for {friend_mail}")
            return None
        # "{lat,lon}" 形式をパース
        lat, lon = map(float, loc_str.strip("{}").split(","))
        print(f"👥 [友人位置情報取得] {friend_mail}: 緯度 {lat:.6f}, 経度 {lon:.6f}")
        return lat, lon
    except Exception as e:
        print(f"⚠️ map_service.fetch_friend_location: {e}")
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

        print(f"📍 [位置情報処理] ユーザー: {mail} (自分のみ操作), 緯度: {lat:.6f}, 経度: {lon:.6f}")
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
            # ⚠️ WHERE mail = {mail} という条件で更新 - 自分のメールアドレスに対してのみ
            pres = requests.patch(url, headers=headers_base, params={"mail": f"eq.{mail}"}, data=json.dumps({"location": loc_str, "update_at": datetime.utcnow().isoformat() + "Z"}))
            if pres.status_code in (200, 204):
                print(f"✅ [位置情報更新成功] {mail} の行を更新, 緯度: {lat:.6f}, 経度: {lon:.6f}")
                return True
        except Exception as e:
            print(f"⚠️ save_my_location PATCH error: {e}")

        # PATCHで更新できなければ、POSTで upsert を試す（Prefer ヘッダで merge-duplicates を指定）
        headers_insert = headers_base.copy()
        headers_insert["Prefer"] = "resolution=merge-duplicates"
        insert_url = f"{url}?on_conflict=mail"
        try:
            # on_conflict=mail で自分のメールアドレス用の行のみ操作
            ires = requests.post(insert_url, headers=headers_insert, data=json.dumps(payload))
            if ires.status_code in (200, 201, 204):
                print(f"✅ [位置情報登録成功] {mail} の行を作成/更新, 緯度: {lat:.6f}, 経度: {lon:.6f}")
                return True
            else:
                print(f"⚠️ save_my_location: supabase returned {ires.status_code} {ires.text}")
        except Exception as e:
            print("⚠️ save_my_location: post error", e)
    except Exception as e:
        print("⚠️ map_service.save_my_location:", e)
    return False


def save_meeting(lat, lon, place_name=None):
    """meetingsテーブルにデータを保存
    
    Args:
        lat: 緯度
        lon: 経度
        place_name: 場所の名前（建物名のみ）、Noneの場合はnullで保存
    
    Returns:
        meeting_id（UUID）、または None
    """
    print(f"")
    print(f"=" * 60)
    print(f"🏁 save_meeting() 開始")
    print(f"=" * 60)
    try:
        url = f"{SUPABASE_URL}/rest/v1/meetings"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # location形式: 複数の形式を試せるように準備
        # PostgreSQL point型の場合: (lon,lat) または "(lon,lat)"
        # text型の場合: "{lat,lon}" または "lat,lon"
        location_value = "{" + f"{lat},{lon}" + "}"  # デフォルト形式
        
        payload = {
            "location": location_value,
            "place_name": place_name if place_name else None,
            "status": True
        }
        
        print(f"📝 送信データ:")
        print(f"   - location: {payload['location']} (形式: text配列)")
        print(f"   - place_name: {payload['place_name']}")
        print(f"   - status: {payload['status']}")
        print(f"📤 meetingsテーブルへPOST送信中...")
        
        res = requests.post(url, headers=headers, data=json.dumps(payload))
        
        print(f"📥 レスポンス受信:")
        print(f"   - status_code: {res.status_code}")
        print(f"   - response: {res.text[:200]}")  # 最初の200文字
        
        if res.status_code in (200, 201):
            data = res.json()
            print(f"✅ POSTリクエスト成功")
            print(f"   - データ型: {type(data)}")
            print(f"   - データ内容: {data}")
            
            # レスポンスがリスト形式の場合と単一オブジェクト形式に対応
            if isinstance(data, list):
                if len(data) > 0:
                    meeting_id = data[0].get("id")
                    print(f"   - リスト形式のレスポンス、最初の要素からID取得")
                else:
                    print(f"❌ レスポンスが空のリスト")
                    return None
            else:
                meeting_id = data.get("id")
                print(f"   - オブジェクト形式のレスポンス、IDを直接取得")
            
            if meeting_id:
                print(f"")
                print(f"🎉 meetingsテーブルへの保存成功!")
                print(f"   - meeting_id: {meeting_id}")
                print(f"   - 座標: ({lat:.6f}, {lon:.6f})")
                print(f"=" * 60)
                return meeting_id
            else:
                print(f"❌ レスポンスにIDが含まれていません: {data}")
                print(f"=" * 60)
                return None
        else:
            print(f"❌ POSTリクエスト失敗")
            print(f"   - status_code: {res.status_code}")
            print(f"   - エラー内容: {res.text}")
            print(f"=" * 60)
            return None
    except Exception as e:
        print(f"❌ save_meeting() で例外発生: {e}")
        import traceback
        traceback.print_exc()
        print(f"=" * 60)
        return None


def save_meeting_shares(user_mail, meeting_id):
    """meeting_sharesテーブルにデータを保存
    
    Args:
        user_mail: ユーザーのメールアドレス
        meeting_id: meetings テーブルの ID
    
    Returns:
        True: 保存成功、False: エラー
    """
    print(f"")
    print(f"=" * 60)
    print(f"🏁 save_meeting_shares() 開始")
    print(f"=" * 60)
    try:
        url = f"{SUPABASE_URL}/rest/v1/meeting_shares"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        payload = {
            "user_mail": user_mail,
            "meeting_id": meeting_id,
            "status": True
        }
        
        print(f"📝 送信データ:")
        print(f"   - user_mail: {payload['user_mail']}")
        print(f"   - meeting_id: {payload['meeting_id']}")
        print(f"   - status: {payload['status']}")
        print(f"📤 meeting_sharesテーブルへPOST送信中...")
        
        res = requests.post(url, headers=headers, data=json.dumps(payload))
        
        print(f"📥 レスポンス受信:")
        print(f"   - status_code: {res.status_code}")
        print(f"   - response: {res.text[:200]}")  # 最初の200文字
        
        if res.status_code in (200, 201):
            print(f"")
            print(f"🎉 meeting_sharesテーブルへの保存成功!")
            print(f"   - user_mail: {user_mail}")
            print(f"   - meeting_id: {meeting_id}")
            print(f"=" * 60)
            return True
        else:
            print(f"❌ POSTリクエスト失敗")
            print(f"   - status_code: {res.status_code}")
            print(f"   - エラー内容: {res.text}")
            print(f"=" * 60)
            return False
    except Exception as e:
        print(f"❌ save_meeting_shares() で例外発生: {e}")
        import traceback
        traceback.print_exc()
        print(f"=" * 60)
        return False


def check_meeting_shares_status(user_mail):
    """meeting_sharesテーブルで、user_mailでステータスがtrueのものが存在するか確認
    
    Args:
        user_mail: ユーザーのメールアドレス
    
    Returns:
        True: 存在する、False: 存在しない
    """
    print(f"")
    print(f"=" * 60)
    print(f"🏁 check_meeting_shares_status() 開始")
    print(f"=" * 60)
    try:
        url = f"{SUPABASE_URL}/rest/v1/meeting_shares"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        params = {
            "select": "id",
            "user_mail": f"eq.{user_mail}",
            "status": "eq.true"
        }
        
        print(f"📝 検索条件:")
        print(f"   - user_mail: {user_mail}")
        print(f"   - status: true")
        print(f"📤 meeting_sharesテーブルへGET送信中...")
        
        res = requests.get(url, headers=headers, params=params)
        
        print(f"📥 レスポンス受信:")
        print(f"   - status_code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            has_active = len(data) > 0
            print(f"   - 取得件数: {len(data)}件")
            print(f"")
            if has_active:
                print(f"✅ アクティブなミーティング共有が存在します")
            else:
                print(f"ℹ️  アクティブなミーティング共有は存在しません")
            print(f"   - 結果: {has_active}")
            print(f"=" * 60)
            return has_active
        else:
            print(f"❌ GETリクエスト失敗")
            print(f"   - status_code: {res.status_code}")
            print(f"=" * 60)
            return False
    except Exception as e:
        print(f"❌ check_meeting_shares_status() で例外発生: {e}")
        import traceback
        traceback.print_exc()
        print(f"=" * 60)
        return False