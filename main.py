import requests
import re
import os
import time
from datetime import datetime, timedelta, timezone

# 설정
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

def send_slack_message(text, image_url=None):
    payload = {"text": text}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "text": "메뉴 이미지"}]
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"   ⚠️ 슬랙 전송 실패: {e}")

def get_korea_today_keywords():
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    # 정규식으로 찾을 날짜 패턴들
    return [
        korea_time.strftime("%y.%m.%d"),   # 24.11.20
        korea_time.strftime("%Y. %m. %d"), # 2024. 11. 20.
        korea_time.strftime("%m월 %d일")   # 11월 20일
    ]

def extract_menu_from_html(html_text, keywords):
    """
    HTML 태그 파싱 대신, 텍스트 전체에서 날짜와 메뉴를 찾습니다.
    """
    # 1. 소스코드 내의 모든 텍스트 정리 (유니코드 등 변환)
    # 카카오 데이터는 보통 "description":"메뉴내용..." 형태로 숨어있음
    
    for kw in keywords:
        if kw in html_text:
            print(f"      👉 소스코드 내에서 날짜 키워드 '{kw}' 발견!")
            
            # 날짜 주변의 텍스트를 잘라서 가져오기 (간이 파싱)
            # 해당 날짜가 등장한 위치를 찾음
            idx = html_text.find(kw)
            
            # 날짜 뒤에 있는 내용 300자 추출 (보통 메뉴가 뒤에 있음)
            # 앞뒤로 넉넉하게 잘라서 분석
            snippet = html_text[idx:idx+500]
            
            # 너무 지저분한 기호 제거
            clean_snippet = re.sub(r'[{"},:;]', ' ', snippet)
            
            return clean_snippet
            
    return None

def get_lunch_menu():
    print("🕵️‍♀️ [데이터 발굴 모드] 숨겨진 텍스트 데이터를 찾습니다...")
    
    today_keywords = get_korea_today_keywords()
    print(f"   🔍 찾는 날짜: {today_keywords}")

    # 모바일 브라우저인 척 위장
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9"
    }

    max_retries = 36
    found_status = {name: False for name in RESTAURANTS}

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                if found_status[name]: continue

                print(f"\n[{name}] 데이터 다운로드 중...")
                
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    # 내용이 너무 짧으면 차단된 것
                    if len(response.text) < 1000:
                        print(f"   ⚠️ 내용이 너무 짧습니다 (차단 의심). 길이: {len(response.text)}")
                        print(f"   내용 미리보기: {response.text[:100]}")
                        continue
                        
                    # 정규식/단순검색으로 날짜 찾기
                    menu_snippet = extract_menu_from_html(response.text, today_keywords)
                    
                    if menu_snippet:
                        print(f"   🎉 [{name}] 오늘짜 데이터를 찾았습니다!")
                        print(f"   내용 일부: {menu_snippet[:50]}...")
                        
                        # 이미지 URL 찾기 (http~.jpg 패턴 검색)
                        img_match = re.search(r'https?://\S+?(jpg|png|jpeg)', response.text)
                        img_url = img_match.group(0) if img_match else None
                        
                        # 슬랙 전송
                        msg_text = f"🍱 [{name}] 오늘 메뉴 발견!\n(내용 일부: {menu_snippet[:100]}...)"
                        # 링크도 같이 줌
                        msg_text += f"\n🔗 바로가기: {url}"
                        
                        if img_url:
                            # 썸네일용 url 보정
                            img_url = img_url.replace('"', '').replace('\\', '')
                            send_slack_message(msg_text, img_url)
                        else:
                            send_slack_message(msg_text)
                        
                        found_status[name] = True
                    else:
                        print("   ❌ 소스코드 안에 오늘 날짜가 없습니다.")

                except Exception as e:
                    print(f"   ⚠️ 에러: {e}")

            if all(found_status.values()):
                print("\n🚀 모든 식당 완료! 퇴근합니다.")
                return

            print(f"--- 5분 대기 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간 기다렸지만 데이터를 못 찾았습니다.")

    except Exception as e:
        print(f"치명적 오류: {e}")

if __name__ == "__main__":
    get_lunch_menu()
