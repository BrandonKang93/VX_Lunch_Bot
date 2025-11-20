import requests
from bs4 import BeautifulSoup
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
    return [
        korea_time.strftime("%y.%m.%d"),   # 24.11.20 (카카오 기본)
        korea_time.strftime("%Y. %m. %d"), # 2024. 11. 20. (가끔 보임)
        korea_time.strftime("%m월 %d일")   # 11월 20일
    ]

def get_lunch_menu():
    print("🕵️‍♀️ [구글봇 모드] 검색 엔진인 척 접근하여 데이터를 가져옵니다...")
    
    today_keywords = get_korea_today_keywords()
    print(f"   🔍 찾는 날짜 키워드: {today_keywords} (또는 '분 전', '시간 전')")

    # 구글 검색 로봇의 헤더 (차단 회피용)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # 3시간 반복 (36회)
    max_retries = 36
    found_status = {name: False for name in RESTAURANTS}

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                if found_status[name]: continue

                print(f"\n[{name}] 페이지 읽는 중...")
                
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code != 200:
                        print(f"   ⚠️ 접속 실패 (상태코드: {response.status_code})")
                        continue
                    
                    # HTML 파싱
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 게시글 목록 찾기 (div.post_item)
                    posts = soup.select("div.post_item")
                    
                    if not posts:
                        print("   ⚠️ 페이지는 열렸으나 게시글을 못 찾았습니다. (JavaScript 전용 페이지일 가능성)")
                        # 혹시 HTML 내용을 보고 싶으면 아래 주석 해제
                        # print(soup.text[:300])
                        continue

                    # 상위 3개 글 확인
                    for post in posts[:3]:
                        try:
                            # 날짜 확인
                            date_element = post.select_one("span.txt_date")
                            if not date_element: continue
                            
                            post_date = date_element.get_text(strip=True)
                            
                            # 오늘인지 판별
                            is_today = False
                            if "분 전" in post_date or "시간 전" in post_date:
                                is_today = True
                            else:
                                for kw in today_keywords:
                                    if kw in post_date:
                                        is_today = True
                                        break
                            
                            if is_today:
                                print(f"   🎉 [{name}] 오늘 메뉴 발견! ({post_date})")
                                
                                # 이미지 URL 추출
                                img_tag = post.select_one("img")
                                img_url = None
                                if img_tag and img_tag.get('src'):
                                    img_url = img_tag['src'].replace('fname=', '') # 썸네일 원본화
                                    # http로 시작하지 않으면(상대경로) 처리
                                    if not img_url.startswith('http'):
                                        img_url = None 

                                post_text = post.get_text(strip=True)

                                if img_url:
                                    send_slack_message(f"🍱 [{name}] 오늘 메뉴가 도착했습니다!", img_url)
                                else:
                                    send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post_text[:200]}...")
                                
                                found_status[name] = True
                                break
                        except Exception as e:
                            print(f"   글 분석 중 에러: {e}")
                            continue

                except Exception as e:
                    print(f"   ⚠️ 요청 중 에러: {e}")

            if all(found_status.values()):
                print("\n🚀 모든 식당 전송 완료! 퇴근합니다.")
                return

            print(f"--- 5분 대기 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간을 기다렸지만 메뉴를 가져오지 못했습니다.")

    except Exception as e:
        print(f"치명적 오류: {e}")

if __name__ == "__main__":
    get_lunch_menu()
