from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import re
from datetime import datetime

# 슬랙 주소
SLACK_WEBHOOK_URL = "https://hooks.slack.com/triggers/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"

RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

def send_slack_message(text, image_url=None):
    # [수정됨] 복잡한 포맷 다 버리고, 그냥 텍스트 뒤에 링크를 붙여서 보냅니다.
    # 슬랙이 링크를 인식해서 이미지를 자동으로 보여줍니다.
    
    final_text = text
    if image_url:
        final_text += f"\n\n👇 메뉴 이미지 보기 👇\n{image_url}"
    
    payload = {"text": final_text}
    
    try:
        print(f"   📤 슬랙 전송 중... (내용: {final_text[:30]}...)")
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"   ⚠️ 슬랙 전송 에러: {e}")

def get_today_keywords():
    now = datetime.now()
    return [
        now.strftime("%y.%m.%d"),   # 24.11.20
        now.strftime("%y/%m/%d"),   # 24/11/20
        now.strftime("%m월 %d일"),  # 11월 20일
        now.strftime("%m/%d")       # 11/20
    ]

def extract_url_regex(style_string):
    if not style_string: return None
    match = re.search(r'url\((?:["\']?)(http[^"\')]+)(?:["\']?)\)', style_string)
    if match:
        return match.group(1)
    return None

def get_lunch_menu():
    print("🚀 [심플 모드] 이미지 링크를 텍스트로 직접 보냅니다...")
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    
    wait = WebDriverWait(driver, 10)
    today_keywords = get_today_keywords()
    found_status = {name: False for name in RESTAURANTS}
    
    try:
        print(f"🔍 오늘 날짜 키워드: {today_keywords}")
        
        for name, url in RESTAURANTS.items():
            print(f"\n[{name}] 접속 중...")
            driver.get(url)
            time.sleep(3)
            
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.area_card")))
                posts = driver.find_elements(By.CSS_SELECTOR, "div.area_card")
                
                print(f"   ✅ 게시물 {len(posts)}개 로딩 완료")

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
                        print(f"   🎉 {name} 오늘 메뉴 찾음!")
                        
                        img_url = None
                        try:
                            thumb_div = post.find_element(By.CSS_SELECTOR, "div.wrap_fit_thumb")
                            style_attr = thumb_div.get_attribute("style")
                            img_url = extract_url_regex(style_attr)
                            print(f"   👉 이미지 주소 추출: {img_url}")
                        except:
                            try:
                                img_tag = post.find_element(By.TAG_NAME, "img")
                                img_url = img_tag.get_attribute("src")
                            except:
                                pass

                        if img_url:
                            img_url = img_url.replace("fname=", "")
                            # [중요] 이미지가 있어도 텍스트 함수로 보냅니다
                            send_slack_message(f"🍱 [{name}] 오늘 메뉴 도착!", img_url)
                        else:
                            print("   ⚠️ 이미지 없음, 텍스트만 전송")
                            send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post_text[:200]}")
                        
                        found_status[name] = True
                        break 
            
            except Exception as e:
                print(f"   ⚠️ {name} 탐색 중 에러: {e}")
                
        print("\n--------------------------------")
        if all(found_status.values()):
            print("✅ 완료! 슬랙을 확인하세요.")
        else:
            print("❌ 일부 실패.")
            
    except Exception as e:
        print(f"에러: {e}")
    finally:
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
