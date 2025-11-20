from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import time
import os
from datetime import datetime, timedelta, timezone

# 설정
RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def get_korea_today_formatted():
    # 카카오 날짜 형식에 맞춤 (예: 25.11.20) -> 점(.)으로 구분
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    return korea_time.strftime("%y.%m.%d") 

def send_slack_message(text, image_url=None):
    payload = {"text": text}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "text": "메뉴 이미지"}]
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def get_lunch_menu():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    # 제대로 될 때까지 기다리는 횟수 (3시간 = 36회)
    # 테스트할 때는 1로 줄여서 바로 확인 가능
    max_retries = 36
    
    found_status = {name: False for name in RESTAURANTS}
    today_str = get_korea_today_formatted() # 예: 24.11.20
    
    print(f"🔍 [기준 날짜] 오늘은 '{today_str}' 입니다.")

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                if found_status[name]: continue # 이미 찾은 곳은 패스

                print(f"[{name}] 확인 중...")
                driver.get(url)
                time.sleep(3)
                
                posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
                if not posts: continue

                # 상위 3개 글 날짜 확인
                for post in posts[:3]:
                    try:
                        # 카카오 채널 날짜 위치 (span.txt_date)
                        date_element = post.find_element(By.CSS_SELECTOR, "span.txt_date")
                        post_date = date_element.text # 예: "24.11.20" 또는 "1시간 전"
                        
                        # 조건: 날짜가 오늘 날짜와 같거나, "분 전", "시간 전"이라고 되어 있으면 오늘 글임!
                        is_today = (today_str in post_date) or ("분 전" in post_date) or ("시간 전" in post_date)
                        
                        if is_today:
                            print(f"   ✅ 오늘 게시물 발견! (작성시간: {post_date})")
                            post_text = post.text
                            
                            # 이미지 찾기
                            try:
                                img_tag = post.find_element(By.TAG_NAME, "img")
                                img_url = img_tag.get_attribute("src").replace("fname=", "")
                                send_slack_message(f"🍱 [{name}] 오늘 메뉴가 도착했습니다!", img_url)
                            except:
                                send_slack_message(f"🍱 [{name}] 오늘 메뉴 (텍스트) 입니다.\n{post_text[:200]}...")
                            
                            found_status[name] = True
                            break # 해당 식당 찾았으니 다음 식당으로

                    except Exception as e:
                        print(f"   ⚠️ 날짜 확인 중 에러: {e}")
                        continue

            if all(found_status.values()):
                print("🚀 모든 식당 메뉴 전송 완료! 퇴근합니다.")
                return

            print(f"--- 아직 안 올라온 곳이 있어 5분 뒤 다시 봅니다 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간을 기다렸지만 아직 메뉴가 안 올라왔어요.")

    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
