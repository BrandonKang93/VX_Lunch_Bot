import requests
import json
import os
import time
from datetime import datetime, timedelta, timezone

# 설정
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# 식당 ID (URL 맨 뒤에 있는 그 영어 코드)
RESTAURANTS = {
    "그린쿡": "_yxgQDb",     # https://pf.kakao.com/_yxgQDb
    "런치스토리": "_Fwpwn"   # https://pf.kakao.com/_Fwpwn
}

def send_slack_message(text, image_url=None):
    payload = {"text": text}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "text": "메뉴 이미지"}]
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"슬랙 전송 실패: {e}")

def get_korea_today_date():
    # 한국 시간 기준 오늘 날짜 (YYYY-MM-DD)
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    return korea_time.strftime("%Y-%m-%d")

def get_lunch_menu():
    today_str = get_korea_today_date()
    print(f"🔍 [API 모드] 오늘({today_str}) 메뉴를 데이터 서버에서 직접 조회합니다.")

    # 3시간(36회) 반복
    max_retries = 36
    found_status = {name: False for name in RESTAURANTS}

    try:
        for i in range(max_retries):
            for name, profile_id in RESTAURANTS.items():
                if found_status[name]: continue

                print(f"[{name}] 데이터 조회 중...")
                
                # 카카오 채널의 진짜 데이터 창고(API) 주소
                api_url = f"https://pf-w4-web-api.kakao.com/profile/web/profiles/{profile_id}/posts?page=0&count=5"
                
                # 사람인 척 위장하는 헤더
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": f"https://pf.kakao.com/{profile_id}",
                    "Accept-Language": "ko-KR,ko;q=0.9"
                }

                try:
                    response = requests.get(api_url, headers=headers, timeout=10)
                    
                    if response.status_code != 200:
                        print(f"   ⚠️ 접속 실패 (상태코드: {response.status_code})")
                        continue

                    data = response.json()
                    posts = data.get('items', [])

                    if not posts:
                        print("   ⚠️ 게시글 데이터가 없습니다.")
                        continue

                    # 최신 글 3개 확인
                    is_today = False
                    for post in posts[:3]:
                        # 작성 시간 확인 (예: '2025-11-20 10:30:00' 또는 timestamp)
                        created_at = post.get('created_at', '') # 2025-11-20 ... 형식으로 옴
                        
                        print(f"   📄 최신글 날짜: {created_at}")

                        if today_str in created_at:
                            print(f"   🎉 [{name}] 오늘 메뉴 데이터 발견!")
                            
                            # 이미지 URL 추출
                            media = post.get('media', [])
                            img_url = None
                            if media and len(media) > 0:
                                img_url = media[0].get('url') # 이미지 주소
                            
                            # 본문 내용
                            content = post.get('title', '')
                            
                            if img_url:
                                send_slack_message(f"🍱 [{name}] 오늘 메뉴가 도착했습니다!", img_url)
                            else:
                                send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{content}")
                            
                            found_status[name] = True
                            is_today = True
                            break
                    
                    if not is_today:
                         print("   ❌ 아직 오늘 날짜 글이 API에 없습니다.")

                except Exception as e:
                    print(f"   ⚠️ 에러 발생: {e}")

            if all(found_status.values()):
                print("🚀 모든 식당 전송 완료! 퇴근합니다.")
                return

            print(f"--- 5분 대기 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간을 기다렸지만 메뉴를 가져오지 못했습니다.")

    except Exception as e:
        print(f"치명적 오류: {e}")

if __name__ == "__main__":
    get_lunch_menu()
