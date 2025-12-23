from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
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
        if not SLACK_WEBHOOK_URL:
            print("   ⚠️ SLACK_WEBHOOK_URL 이 설정되지 않아 전송을 건너뜁니다.")
            return
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=15, verify=False)
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

def _get_retry_config():
    """
    B 요구사항: 두 식당 모두 찾을 때까지 재시도하되, 무한 대기는 방지.
    환경변수로 조절 가능:
      - MAX_ATTEMPTS (기본 12)
      - RETRY_SLEEP_SEC (기본 300 = 5분)
      - MAX_RUNTIME_MIN (기본 60)
    """
    def _to_int(name, default):
        try:
            return int(os.environ.get(name, str(default)))
        except Exception:
            return default

    max_attempts = max(1, _to_int("MAX_ATTEMPTS", 12))
    sleep_sec = max(5, _to_int("RETRY_SLEEP_SEC", 300))
    max_runtime_min = max(1, _to_int("MAX_RUNTIME_MIN", 60))
    return max_attempts, sleep_sec, max_runtime_min

def _create_driver():
    options = Options()

    # GitHub Actions / 서버 환경에서 기본적으로 headless로 동작하도록
    headless_arg = os.environ.get("CHROME_HEADLESS_ARG", "--headless=new")
    if headless_arg:
        options.add_argument(headless_arg)

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # webdriver-manager로 드라이버 자동 설치/매칭
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def _check_restaurant(driver, wait, name, url, today_keywords):
    print(f"\n[{name}] 접속 중...")
    driver.get(url)

    # 카카오채널 페이지 로딩 대기
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
                    is_today = True
                    break

        if not is_today:
            continue

        print(f"   🎉 {name} 발견!")

        img_url = None
        try:
            thumb_div = post.find_element(By.CSS_SELECTOR, "div.wrap_fit_thumb")
            style_attr = thumb_div.get_attribute("style")
            img_url = extract_url_regex(style_attr)
        except Exception:
            pass

        if not img_url:
            try:
                img_tag = post.find_element(By.TAG_NAME, "img")
                img_url = img_tag.get_attribute("src")
            except Exception:
                pass

        if img_url:
            img_url = img_url.replace("fname=", "")
            send_slack_message(f"🍱 [{name}] 오늘 메뉴 도착!", img_url)
        else:
            send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post_text[:200]}")

        return True

    return False

def get_lunch_menu():
    print("🚀 [워크플로 모드] (B) 두 식당 모두 확인될 때까지 재시도합니다...")

    max_attempts, sleep_sec, max_runtime_min = _get_retry_config()
    print(f"⏱️ 재시도 설정: MAX_ATTEMPTS={max_attempts}, RETRY_SLEEP_SEC={sleep_sec}, MAX_RUNTIME_MIN={max_runtime_min}")

    driver = _create_driver()
    wait = WebDriverWait(driver, 15)
    found_status = {name: False for name in RESTAURANTS}
    start_ts = time.time()
    
    try:
        for attempt in range(1, max_attempts + 1):
            elapsed_min = (time.time() - start_ts) / 60.0
            if elapsed_min >= max_runtime_min:
                print(f"\n⛔ 최대 실행 시간({max_runtime_min}분) 초과로 중단합니다.")
                break

            today_keywords = get_today_keywords()
            print(f"\n🔁 시도 {attempt}/{max_attempts} (경과 {elapsed_min:.1f}분)")
            print(f"🔍 날짜 키워드: {today_keywords}")

            for name, url in RESTAURANTS.items():
                if found_status.get(name):
                    continue

                try:
                    found_status[name] = _check_restaurant(driver, wait, name, url, today_keywords)
                except Exception as e:
                    print(f"   ⚠️ {name} 에러: {e}")

            if all(found_status.values()):
                print("\n✅ 완료! (두 식당 모두 확인)")
                return

            remaining = [k for k, v in found_status.items() if not v]
            print(f"\n⌛ 아직 미확인: {remaining}")

            # 마지막 시도가 아니면 대기 후 재시도
            if attempt < max_attempts:
                # 다음 루프에서 max_runtime_min 초과 여부를 다시 확인
                time.sleep(sleep_sec)

        # 여기까지 왔으면 모두 찾지 못함
        remaining = [k for k, v in found_status.items() if not v]
        print(f"\n❌ 시간/횟수 제한으로 종료. 미확인: {remaining}")
        send_slack_message(f"❌ 오늘 메뉴를 끝까지 못 찾았습니다. 미확인: {', '.join(remaining)}")
            
    except Exception as e:
        print(f"에러: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
