import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class NewsCrawler:
    def __init__(self):
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.base_url = "https://openapi.naver.com/v1/search/news.json"

    def fetch_news(self, query, display=20):
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {
            "query": query,
            "display": display,
            "sort": "sim"
        }
        
        response = requests.get(self.base_url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            print(f"Error fetching news for {query}: {response.status_code}")
            return []

    def get_daily_reports(self):
        from email.utils import parsedate_to_datetime
        from datetime import timezone
        
        now = datetime.now(timezone.utc)
        # 2,000건 이상의 방대한 데이터를 확보하기 위한 키워드 대폭 확장
        categories = {
            "정책 및 입법 (필수 분석)": [
                "장애인 권리보장법", "탈시설 지원법", "장애인 예산", "국정감사 장애인", "장애인 정책 요", "장애인 등급제 폐지", "장애인 연금", "활동지원서비스"
            ],
            "이동권 및 접근성 (현장의 목소리)": [
                "장애인 이동권 투쟁", "전장연 시위", "저상버스 도입", "장애인 콜택시", "특별교통수단", "키오스크 접근성", "휠체어 접근성", "배리어프리"
            ],
            "고용, 교육 및 자립": [
                "장애인 의무고용", "장애인 일자리", "특수교육", "통합교육", "발달장애인 주간활동", "장애인 자립생활", "장애인 야학"
            ],
            "인권 침해 및 학대 (심층 취재)": [
                "장애인 학대", "시설 비리", "장애인 차별", "발달장애인 실종", "장애여성 인권", "장애인 혐오"
            ]
        }
        all_news = {}
        
        for cat, kws in categories.items():
            cat_items = []
            display_count = 60
            
            # 모든 카테고리에 대해 지난 24시간 필터링 적용
            hours_limit = 24
            
            for kw in kws:
                news_items = self.fetch_news(kw, display=display_count)
                for item in news_items:
                    pub_date_str = item.get("pubDate")
                    if pub_date_str:
                        try:
                            pub_date = parsedate_to_datetime(pub_date_str)
                            if now - pub_date > timedelta(hours=hours_limit):
                                continue
                        except:
                            pass
                            
                    cat_items.append({
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "link": item.get("originallink", item.get("link", ""))
                    })
            all_news[cat] = cat_items
            
        return all_news

if __name__ == "__main__":
    crawler = NewsCrawler()
    results = crawler.get_daily_reports()
    for kw, items in results.items():
        print(f"Keyword: {kw}, Found: {len(items)} items")
