from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import re
import os
from datetime import datetime, timedelta, timezone

# ⚠️ 워크플로 웹훅 주소 (triggers/...) 그대로 사용
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

def send_slack_message(text, image_url=None):
    # [핵심 변경] 
    # 워크플로 빌더에게 보낼 데이터를 준비합니다.
    # 텍스트와 이미지 주소를 '분리'해서 보낼 수도 있지만,
    # 가장 확실한 건 텍스트 안에 주소를 포함시키는 것입니다.
    
    final_message = text
    if image_url:
        # 주소 앞뒤로 공백을 넣어 슬랙이 링크를 잘 인식하게 합니다.
        final_message += f"\n\n{image_url}\n" 

    # 워크플로 빌더의 변수 이름이 'text'라고 가정합니다.
    payload = {"text": final_message}
    
    try:
        print(f"   📤 전송 중... (내용: {final_message[:30]}...)")
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"   ⚠️ 전송 에러: {e}")

def get_today_keywords():
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    return [
        korea_time.strftime("%y.%m.%d"),
        korea_time.strftime("%y/%m/%d"),
        korea_time.strftime("%m월 %d일"),
        korea_time.strftime("%m/%d")
    ]

def extract_url_regex(style_string):
    if not style_string: return None
    match = re.search(r'url\((?:["\']?)(http[^"\')]+)(?:["\']?)\)', style_string)
    if match:
        return match.group(1)
    return None

def get_lunch_menu():
    print("🚀 [워크플로 모드] 이미지 미리보기를 유도합니다...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    today_keywords = get_today_keywords()
    found_status = {name: False for name in RESTAURANTS}
    
    try:
        print(f"🔍 날짜 키워드: {today_keywords}")
        
        for name, url in RESTAURANTS.items():
            print(f"\n[{name}] 접속 중...")
            driver.get(url)
            time.sleep(3)
            
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.area_card")))
                posts = driver.find_elements(By.CSS_SELECTOR, "div.area_card")
                print(f"   ✅ 게시물 {len(posts)}개 로딩")

                for post in posts[:5]:
                    post_text = post.text
                    
                    is_today = False
                    if "분 전" in post_text or "시간 전" in post_text:
                        is_today = True
                    else:
                        for kw in today_keywords:
                            if kw in post_text:
                                is_today = True; break
                    
                    if is_today:
                        print(f"   🎉 {name} 발견!")
                        
                        img_url = None
                        try:
                            thumb_div = post.find_element(By.CSS_SELECTOR, "div.wrap_fit_thumb")
                            style_attr = thumb_div.get_attribute("style")
                            img_url = extract_url_regex(style_attr)
                        except: pass
                        
                        if not img_url:
                            try:
                                img_tag = post.find_element(By.TAG_NAME, "img")
                                img_url = img_tag.get_attribute("src")
                            except: pass

                        if img_url:
                            img_url = img_url.replace("fname=", "")
                            send_slack_message(f"🍱 [{name}] 오늘 메뉴 도착!", img_url)
                        else:
                            send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post_text[:200]}")
                        
                        found_status[name] = True
                        break 
            
            except Exception as e:
                print(f"   ⚠️ {name} 에러: {e}")

        if all(found_status.values()):
            print("✅ 완료!")
        else:
            print("❌ 일부 실패")
            
    except Exception as e:
        print(f"에러: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
