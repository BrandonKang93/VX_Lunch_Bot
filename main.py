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
    return [
        korea_time.strftime("%y.%m.%d"),  # 24.11.20
        korea_time.strftime("%y/%m/%d"),  # 24/11/20
        korea_time.strftime("%Y. %m. %d") # 2024. 11. 20.
    ]

def get_lunch_menu():
    options = Options()
    # [핵심 1] 최신 헤드리스 모드 사용 (탐지 회피율 높음)
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # [핵심 2] 자동화 봇 표시 제거 (스텔스 설정)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    # [핵심 3] 자바스크립트로 webdriver 속성 숨기기 (가장 강력한 회피법)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    wait = WebDriverWait(driver, 15) # 15초 대기
    max_retries = 36
    
    found_status = {name: False for name in RESTAURANTS}
    today_keywords = get_today_keywords()
    
    print(f"🔍 [시작] 스텔스 모드로 접속합니다. 키워드: {today_keywords}")

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                if found_status[name]: continue

                print(f"[{name}] 접속 시도...")
                driver.get(url)
                
                try:
                    # 로딩 대기 (div.post_item이 뜰 때까지)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.post_item")))
                    
                    posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
                    if not posts: 
                        print("   ⚠️ 목록 요소는 찾았으나 비어있습니다.")
                        continue

                    # 상위 3개 글 확인
                    for post in posts[:3]:
                        try:
                            post_date = post.find_element(By.CSS_SELECTOR, "span.txt_date").text
                            
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
                                try:
                                    img_tag = post.find_element(By.TAG_NAME, "img")
                                    img_url = img_tag.get_attribute("src")
                                    send_slack_message(f"🍱 [{name}] 오늘 메뉴가 도착했습니다!", img_url)
                                except:
                                    send_slack_message(f"🍱 [{name}] 오늘 메뉴 (텍스트) 입니다.\n{post.text[:200]}")
                                
                                found_status[name] = True
                                break
                                
                        except Exception:
                            continue
                            
                except Exception as e:
                    print(f"   ⚠️ 차단되었거나 로딩 실패 (재시도 예정)")
                    # 실패해도 멈추지 않고 다음 식당으로 넘어감

            if all(found_status.values()):
                print("🚀 모든 식당 전송 완료! 퇴근합니다.")
                return

            print(f"--- 메뉴 대기 중... 5분 뒤 다시 봅니다 ({i+1}/{max_retries}) ---")
            time.sleep(300)

        send_slack_message("😢 3시간을 기다렸지만 메뉴를 못 가져왔습니다. (봇 차단 의심)")

    except Exception as e:
        print(f"치명적 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
