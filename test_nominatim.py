#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nominatim APIの動作確認テスト
"""
import requests
import json

def test_nominatim(lat, lon):
    """Nominatim APIをテスト"""
    print(f"🔍 Nominatim API テスト開始")
    print(f"   座標: ({lat}, {lon})")
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "format": "json",
            "lat": lat,
            "lon": lon,
            "language": "ja"
        }
        headers = {
            "User-Agent": "MyLocationApp/1.0"
        }
        
        print(f"📤 API呼び出し中...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"📥 レスポンス受信: status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API応答成功")
            print(f"\n📋 レスポンス内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # address フィールドを確認
            address = data.get('address', {})
            print(f"\n🏠 address フィールド:")
            for key, value in address.items():
                print(f"   {key}: {value}")
            
            # name フィールドを確認
            if 'name' in data:
                print(f"\n🏢 name フィールド: {data['name']}")
            
            # 建物名抽出テスト
            print(f"\n🔍 建物名抽出テスト:")
            info_parts = []
            if 'state' in address:
                info_parts.append(address['state'])
            if 'city' in address:
                info_parts.append(address['city'])
            elif 'county' in address:
                info_parts.append(address['county'])
            if 'suburb' in address:
                info_parts.append(address['suburb'])
            if 'name' in data and data['name'] != address.get('city'):
                info_parts.append(data['name'])
            
            info_text = " / ".join(info_parts)
            print(f"   作成されたinfo_text: {info_text}")
            
            # 盛岡市の後ろを抽出
            parts = [p.strip() for p in info_text.split("/") if p.strip()]
            city_idx = None
            for idx, part in enumerate(parts):
                if "盛岡市" in part:
                    city_idx = idx
                    print(f"   ✅ 盛岡市を発見: index={idx}")
                    break
            
            if city_idx is not None:
                if city_idx + 1 < len(parts):
                    building = " / ".join(parts[city_idx + 1:]).strip()
                    print(f"   ✅ 抽出された建物名: {building}")
                else:
                    print(f"   ⚠️ 盛岡市の後ろにデータがありません")
            else:
                print(f"   ⚠️ 盛岡市が見つかりません")
        else:
            print(f"❌ API呼び出し失敗")
            print(f"   status_code: {response.status_code}")
            print(f"   response: {response.text}")
    
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 盛岡市内のいくつかの座標でテスト
    test_coords = [
        (39.7068, 141.1496),  # 盛岡駅周辺
        (39.7050, 141.1340),  # 盛岡市役所周辺
        (39.6952, 141.1373),  # 岩手県庁周辺
    ]
    
    for lat, lon in test_coords:
        print(f"\n{'='*60}")
        test_nominatim(lat, lon)
        print(f"{'='*60}\n")
