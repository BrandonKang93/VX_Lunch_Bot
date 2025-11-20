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

def get_today_keywords():
    korea_time = datetime.now(timezone.utc) + timedelta(hours=9)
    # 1. "11.20" (가장 흔한 포맷)
    keyword1 = korea_time.strftime("%m.%d")
    # 2. "11/20" (가끔 이렇게 쓰는 경우)
    keyword2 = korea_time.strftime("%m/%d")
    # 3. "11월 20일" (한글 포맷)
    keyword3 = korea_time.strftime("%m월 %d일")
    
    return [keyword1, keyword2, keyword3]

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
    
    # 테스트니까 1번만 확인하고 바로 결과 보고
    max_retries = 1 
    
    today_keywords = get_today_keywords()
    print(f"🔍 [검색 조건] 이 글자들을 찾습니다: {today_keywords}")
    print(f"   (또는 '분 전', '시간 전'도 찾습니다)")

    try:
        for i in range(max_retries):
            for name, url in RESTAURANTS.items():
                print(f"\n--------------------------------")
                print(f"🏢 [{name}] 페이지 접속 중...")
                driver.get(url)
                time.sleep(5) # 로딩 대기
                
                posts = driver.find_elements(By.CSS_SELECTOR, "div.post_item")
                if not posts:
                    print("   ❌ 게시물을 하나도 못 읽어왔습니다. (사이트 구조 변경?)")
                    continue

                print(f"   📄 최신 글 3개를 분석합니다:")
                
                # 상위 3개 글 정밀 분석
                for index, post in enumerate(posts[:3]):
                    try:
                        # 1. 게시 날짜(메타데이터) 확인
                        date_element = post.find_element(By.CSS_SELECTOR, "span.txt_date")
                        post_date_text = date_element.text
                        
                        # 2. 본문 내용 확인
                        post_content = post.text[:30].replace("\n", " ") # 앞 30글자만
                        
                        print(f"   [글 {index+1}] 날짜: '{post_date_text}' / 내용: '{post_content}...'")
                        
                        # 판별 로직
                        is_today = False
                        
                        # A. '방금 전', '1시간 전' 체크
                        if "분 전" in post_date_text or "시간 전" in post_date_text:
                            print("      👉 'n시간 전'이라서 합격!")
                            is_today = True
                        
                        # B. 날짜 키워드 매칭 (11.20 등)
                        if not is_today:
                            for keyword in today_keywords:
                                if keyword in post_date_text or keyword in post_content:
                                    print(f"      👉 키워드('{keyword}') 발견으로 합격!")
                                    is_today = True
                                    break
                        
                        if is_today:
                            print("      🎉 오늘 메뉴 찾았습니다! 슬랙 전송!")
                            try:
                                img_tag = post.find_element(By.TAG_NAME, "img")
                                img_url = img_tag.get_attribute("src").replace("fname=", "")
                                send_slack_message(f"🍱 [{name}] 오늘 메뉴 발견!", img_url)
                            except:
                                send_slack_message(f"🍱 [{name}] 텍스트 메뉴입니다.\n{post.text}")
                            
                            # 찾았으니 다음 식당으로 넘어감
                            break 
                        else:
                             print("      ❌ 오늘 날짜와 다릅니다.")

                    except Exception as e:
                        print(f"      ⚠️ 분석 중 에러: {e}")

            print("\n--------------------------------")
            print("🏁 진단이 끝났습니다. 로그를 확인해주세요.")
            return

    except Exception as e:
        print(f"치명적 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_lunch_menu()
