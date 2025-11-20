from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

def send_slack_message(text, image_url=None):
    payload = {"text": text}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "text": "메뉴 이미지"}]
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def get_today_keywords():
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    # 카카오 날짜 형식 다 잡아내기
    return [
        korea_time.strftime("%y.%m.%d"),  # 24.11.20
        korea_time.strftime("%y/%m/%d"),  # 24/11/20
        korea_time.strftime("%Y. %m. %d") # 2024. 11. 20.
    ]

def get_lunch_menu():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 봇 탐지 회피 옵션 추가
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20) # 최대 20초까지 기다리게 함

    # 3시간(36회) 반복 체크
    max_retries = 36
    
    found_status = {name: False for name in RESTAURANTS}
    today_keywords = get_today_keywords()
    
    print(f"🔍 [시작] 오늘 날짜 키워드: {today_keywords}")

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                if found_status[name]: continue

                print(f"[{name}] 접속 중...")
                driver.get(url)
                
                try:
                    # 핵심: 글 목록(div.post_item)이 뜰 때까지 20초 대기!
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.post_item")))
                    
                    # 로딩 후 요소 가져오기
                    posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
                    
                    # 상위 3개 글 확인
                    for post in posts[:3]:
                        try:
                            # 날짜 요소 가져오기
                            date_element = post.find_element(By.CSS_SELECTOR, "span.txt_date")
                            post_date = date_element.text
                            
                            # 오늘인지 판별 (날짜 일치 or '분 전/시간 전')
                            is_today = False
                            if "분 전" in post_date or "시간 전" in post_date:
                                is_today = True
                            else:
                                for kw in today_keywords:
                                    if kw in post_date:
                                        is_today = True
                                        break
                            
                            if is_today:
                                print(f"   🎉 [{name}] 오늘 메뉴 찾음! ({post_date})")
                                
                                # 이미지 추출 시도
                                try:
                                    img_tag = post.find_element(By.TAG_NAME, "img")
                                    # 썸네일 주소 보정 (fname= 제거 등)
                                    img_url = img_tag.get_attribute("src")
                                    send_slack_message(f"🍱 [{name}] 오늘 메뉴가 도착했습니다!", img_url)
                                except:
                                    send_slack_message(f"🍱 [{name}] 오늘 메뉴 (텍스트) 입니다.\n{post.text[:200]}")
                                
                                found_status[name] = True
                                break # 다음 식당으로
                                
                        except Exception as e:
                            print(f"   글 분석 중 에러(무시): {e}")
                            continue
                            
                except Exception as e:
                    print(f"   ⚠️ 로딩 시간 초과 또는 구조 변경: {e}")
                    # 로딩 실패 시 이번 턴은 넘기고 다음 턴에 재시도

            if all(found_status.values()):
                print("🚀 모든 식당 전송 완료! 퇴근합니다.")
                return

            print(f"--- 아직 안 올라온 곳이 있어 5분 뒤 다시 봅니다 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간을 기다렸지만 메뉴가 안 올라왔어요.")

    except Exception as e:
        print(f"치명적 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
