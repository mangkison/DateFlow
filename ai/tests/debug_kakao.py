import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import json
from dotenv import load_dotenv
import requests

load_dotenv()

print("=" * 60)
print("환경 변수 확인")
print("=" * 60)
kakao_key = os.getenv("KAKAO_KEY")
print(f"KAKAO_KEY 존재 여부: {bool(kakao_key)}")
if kakao_key:
    print(f"KAKAO_KEY 길이: {len(kakao_key)}")
    print(f"KAKAO_KEY 앞 6자리: {kakao_key[:6]}...")

print("\n" + "=" * 60)
print("카카오 Local API 직접 호출")
print("=" * 60)

queries = ["블루보틀 성수", "어니언 성수", "스타벅스 강남", "장인닭갈비 강남점"]

for q in queries:
    print(f"\n--- query: {q} ---")
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    params = {"query": q, "size": 3}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        print(f"Status: {res.status_code}")
        data = res.json()
        if res.status_code != 200:
            print(f"에러 응답: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            docs = data.get("documents", [])
            print(f"검색 결과 {len(docs)}개")
            for d in docs:
                print(
                    f"  - {d.get('place_name')} | "
                    f"{d.get('road_address_name') or d.get('address_name')} | "
                    f"{d.get('place_url')}"
                )
    except Exception as e:
        print(f"예외 발생: {type(e).__name__}: {e}")
