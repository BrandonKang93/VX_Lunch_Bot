from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import time
import os
from datetime import datetime, timedelta, timezone

# 1. 설정: 두 식당의 이름과 주소를 여기에 등록합니다.
RESTAURANTS = {
    "그린쿡": "https://pf.kakao.com/_yxgQDb/posts",
    "런치스토리": "https://pf.kakao.com/_Fwpwn/posts"
}

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# 한국 시간 오늘 날짜 (예: 11/20) - 연도는 뺄 수도 있어서 월/일로 매칭
def get_korea_today_str():
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    return korea_time.strftime("%m/%d") # 예: 11/20

def send_slack_message(text, image_url=None):
    payload = {"text": text}
    if image_url:
        payload["attachments"] = [{"image_url": image_url, "text": "식단 이미지"}]
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def get_lunch_menu():
    # 크롬 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    # 3시간 대기 설정
    # 5분(300초) x 36회 = 180분 (3시간)
    max_retries = 36 
    
    # 메뉴 찾았는지 체크하는 장부 (처음엔 다 False)
    found_status = {name: False for name in RESTAURANTS}
    
    today_str = get_korea_today_str()
    print(f"🔍 [봇 시작] 오늘({today_str}) 메뉴 탐색을 시작합니다. (최대 3시간)")

    try:
        for i in range(max_retries):
            # 모든 식당을 돌면서 확인
            for name, url in RESTAURANTS.items():
                
                # 이미 찾은 식당은 건너뜀
                if found_status[name]:
                    continue

                print(f"[{i+1}회차] '{name}' 확인 중...")
                driver.get(url)
                time.sleep(3) # 페이지 로딩 대기
                
                # 게시물 확인
                posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
                if not posts:
                    continue

                latest_post = posts[0]
                post_text = latest_post.text
                
                # 게시물 내용에 '오늘 날짜(예: 11/20)'가 포함되어 있는지 확인
                # (혹시 날짜 형식이 다를 수 있어 '/'를 빼는 등 유연하게 체크하고 싶다면 수정 가능)
                if today_str in post_text:
                    print(f"🎉 '{name}' 메뉴 발견!")
                    
                    # 이미지 찾기
                    try:
                        img_tag = latest_post.find_element(By.TAG_NAME, "img")
                        img_url = img_tag.get_attribute("src").replace("fname=", "")
                        send_slack_message(f"🍱 [{name}] 오늘({today_str}) 메뉴입니다!", img_url)
                    except:
                        send_slack_message(f"🍱 [{name}] 오늘({today_str}) 메뉴 텍스트입니다.\n{post_text}")
                    
                    # 찾았다고 장부에 기록
                    found_status[name] = True
                
            # 두 식당 모두 찾았는지 확인
            if all(found_status.values()):
                print("🚀 모든 식당의 메뉴를 찾았습니다! 봇을 종료합니다.")
                return # 봇 퇴근!

            # 아직 못 찾은 곳이 있으면 5분 대기
            print(f"--- 아직 메뉴가 안 나온 곳이 있습니다. 5분 뒤 다시 확인합니다. ({i+1}/{max_retries}) ---")
            time.sleep(300)

        # 3시간 동안 반복했는데도 못 찾은 경우
        not_found_list = [name for name, found in found_status.items() if not found]
        print(f"3시간이 지났습니다. 못 찾은 식당: {', '.join(not_found_list)}")
        send_slack_message(f"😢 3시간을 기다렸지만 {', '.join(not_found_list)} 메뉴가 아직 안 올라왔어요.")

    except Exception as e:
        print(f"에러 발생: {e}")
        # 에러 나도 일단 알려줌
        send_slack_message(f"봇 실행 중 오류가 발생했습니다: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
