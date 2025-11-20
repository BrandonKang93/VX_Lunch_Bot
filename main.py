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

# 깃허브 Secret에서 주소 가져오기 (설정 안 했으면 직접 적어도 됨)
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
# 만약 Secret 설정이 귀찮으시면 위 줄을 지우고 아래처럼 직접 넣으세요.
# SLACK_WEBHOOK_URL = "https://hooks.slack.com/triggers/..."

RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

def send_slack_message(text, image_url=None):
    final_text = text
    if image_url:
        final_text += f"\n\n👇 메뉴 이미지 보기 👇\n{image_url}"
    
    payload = {"text": final_text}
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
        print(f"   📤 슬랙 전송 완료")
    except Exception as e:
        print(f"   ⚠️ 슬랙 전송 에러: {e}")

def get_today_keywords():
    # 깃허브 서버(UTC) 시간을 한국 시간(KST)으로 변환
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    return [
        korea_time.strftime("%y.%m.%d"),   # 24.11.20
        korea_time.strftime("%y/%m/%d"),   # 24/11/20
        korea_time.strftime("%m월 %d일"),  # 11월 20일
        korea_time.strftime("%m/%d")       # 11/20
    ]

def extract_url_regex(style_string):
    if not style_string: return None
    match = re.search(r'url\((?:["\']?)(http[^"\')]+)(?:["\']?)\)', style_string)
    if match:
        return match.group(1)
    return None

def get_lunch_menu():
    print("🚀 [GitHub Action] 서버에서 메뉴 탐색을 시작합니다...")
    
    options = Options()
    # [서버 전용 필수 설정]
    options.add_argument("--headless=new")  # 화면 없이 실행 (필수!)
    options.add_argument("--no-sandbox")    # 리눅스 권한 문제 방지
    options.add_argument("--disable-dev-shm-usage") # 메모리 부족 방지
    
    # [중요] PC 화면과 똑같은 구조(area_card)를 보기 위해 해상도 강제 설정
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    
    wait = WebDriverWait(driver, 15)
    today_keywords = get_today_keywords()
    found_status = {name: False for name in RESTAURANTS}
    
    try:
        print(f"🔍 오늘 날짜 키워드(KST): {today_keywords}")
        
        for name, url in RESTAURANTS.items():
            print(f"\n[{name}] 접속 중...")
            driver.get(url)
            time.sleep(3) # 로딩 안정화
            
            try:
                # PC에서 성공했던 'area_card' 찾기 로직
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
                            # 1순위: 썸네일 배경 이미지 (PC 구조)
                            thumb_div = post.find_element(By.CSS_SELECTOR, "div.wrap_fit_thumb")
                            style_attr = thumb_div.get_attribute("style")
                            img_url = extract_url_regex(style_attr)
                        except:
                            pass
                        
                        if not img_url:
                            try:
                                # 2순위: 본문 이미지
                                img_tag = post.find_element(By.TAG_NAME, "img")
                                img_url = img_tag.get_attribute("src")
                            except:
                                pass

                        if img_url:
                            img_url = img_url.replace("fname=", "")
                            send_slack_message(f"🍱 [{name}] 오늘 메뉴 도착!", img_url)
                        else:
                            send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post_text[:200]}")
                        
                        found_status[name] = True
                        break 
            
            except Exception as e:
                print(f"   ⚠️ {name} 탐색 실패: {e}")

        if all(found_status.values()):
            print("✅ 모든 메뉴 전송 완료!")
        else:
            print("❌ 일부 메뉴를 못 찾았습니다.")
            
    except Exception as e:
        print(f"에러: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
