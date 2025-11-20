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

def send_slack_message(text):
    requests.post(SLACK_WEBHOOK_URL, json={"text": text})

def get_lunch_menu():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 윈도우 크기를 크게 설정 (모바일 뷰 꼬임 방지)
    options.add_argument("--window-size=1920,1080") 
    # 한국어 설정 (영문 페이지 뜨는 것 방지)
    options.add_argument("--lang=ko_KR")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    print("🕵️‍♀️ [진단 모드] 봇이 보고 있는 화면을 분석합니다...")

    try:
        for name, url in RESTAURANTS.items():
            print(f"\n▶ [{name}] 접속 시도: {url}")
            driver.get(url)
            time.sleep(5) # 로딩 대기
            
            # 1. 현재 페이지 제목 확인
            print(f"   👉 현재 페이지 제목: {driver.title}")
            
            # 2. 게시물 찾기 시도 (여러가지 이름으로 찾아봄)
            posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
            
            if not posts:
                # 혹시 다른 이름인가? (링크 덩어리)
                posts = driver.find_elements(By.CSS_SELECTOR, "a.link_post")
            
            if posts:
                print(f"   ✅ 게시물 {len(posts)}개 발견! (정상)")
                print(f"   첫번째 글 요약: {posts[0].text[:30]}...")
            else:
                print("   ❌ 게시물 감지 실패.")
                print("   ⚠️ 봇이 보고 있는 HTML 소스코드 (앞부분 500자):")
                print("   ---------------------------------------------------")
                # 소스코드 출력 (이걸 보면 원인을 알 수 있음)
                print(driver.page_source[:500]) 
                print("   ---------------------------------------------------")
                
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
