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
            "문화 예술 및 K-컬처 (정책 및 현안)": [
                "문체부 예산", "문화예술계 블랙리스트", "K-컨텐츠 지원", "문화재청", "저작권법 개정", "영화 발전 기금", "예술인 고용보험", "국립현대미술관", "문화예술 진흥", "스크린 독과점"
            ],
            "체육계 이슈 및 비리 (공정성)": [
                "대한체육회", "축구협회 비리", "국가대표 선발 논란", "체육계 폭력", "생활체육 예산", "스포츠 인권", "안세영", "올림픽 준비", "체육시설 안전", "배드민턴협회", "프로스포츠 공정성"
            ],
            "관광 산업 및 지역 활성화": [
                "한국관광공사", "방한 관광객", "지역 축제 바가지", "관광 수지 적자", "K-관광 로드쇼", "숙박업 규제", "비자 제도 개선", "면세점 위기", "오버투어리즘", "치유 관광"
            ],
            "문체부 행정 및 중요 이슈 (심층)": [
                "유인촌 장관", "문체부 국정감사", "게임물관리위원회", "확률형 아이템", "웹툰 표준계약서", "출판계 불황", "대중문화예술산업 발전법", "AI 저작권", "OTT 규제"
            ]
        }
        all_news = {}
        
        for cat, kws in categories.items():
            cat_items = []
            display_count = 80
            
            # 모든 카테고리에 대해 지난 72시간 필터링 적용 - 기존 168시간(7일)에서 72시간으로 변경
            hours_limit = 72
            
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
