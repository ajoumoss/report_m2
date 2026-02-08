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
            "sort": "date"
        }
        
        response = requests.get(self.base_url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            print(f"Error fetching news for {query}: {response.status_code}")
            return []

    def is_similar(self, str1, str2, threshold=0.6):
        import difflib
        return difflib.SequenceMatcher(None, str1, str2).ratio() > threshold

    def get_daily_reports(self):
        from email.utils import parsedate_to_datetime
        from datetime import timezone
        
        now = datetime.now(timezone.utc)
        
        # [노이즈 필터링 키워드] - 홍보, 행사, 단순 동정 기사 제거
        NOT_WORDS = [
            "축제", "페스티벌", "행사", "개최", "성황리", "기념", "캠페인", "프로모션", "할인", "이벤트", "오픈", "출시", "개막",
            "공연", "콘서트", "팬", "팬덤", "투어", "예매", "굿즈", "기부", "후원", "전달", "봉사", "나눔", "수상", "선정", "인증", "발간", "공개", "촬영", "화보"
        ]

        # [현안 질의형 고품질 쿼리 세트]
        categories = {
            "Basket A: 거버넌스/감사/인사 (핵심)": [
                "문체부 감사원 감사", "문화체육관광부 보조금 부정수급 환수", "문체부 산하기관 회계 비리 징계", 
                "문체부 기관장 인사 논란 낙하산", "문체부 공모 선정 논란 심사위원 회의록", "문체부 국정감사 후속조치 이행"
            ],
            "Basket B: 콘텐츠/저작권/게임 (산업)": [
                "저작권신탁단체 회계 불투명 감사", "저작권 신탁관리단체 징계 시정명령", "웹툰 불공정 계약 표준계약서 문체부",
                "OTT 규제 공백 심의 가이드라인", "방송콘텐츠 제작현장 임금체불 정산지연", "게임 확률형 아이템 위반 제재", "게임물관리위원회 감사 징계"
            ],
            "Basket C: 체육/국제대회/인권 (스포츠)": [
                "대한체육회 회계 감사 징계", "체육단체 보조금 부정수급 환수", "스포츠 폭력 인권 사건 조사 징계",
                "도핑 위반 제재 종목단체", "승부조작 수사 종목단체", "국제대회 유치 예산 타당성 논란"
            ],
            "Basket D: 관광/지역/국립기관 (생활)": [
                "오버투어리즘 대책 관광세 총량제", "바가지요금 민원 축제 국비 지원", "세계유산 개발 충돌 세계유산영향평가",
                "국립박물관 미술관 안전사고 관리부실", "관광공사 사업 예산 집행 논란 감사"
            ],
            "Recall: 기관별 포괄 이슈 (보완)": [
                "문화체육관광부 논란", "한국콘텐츠진흥원 논란", "한국관광공사 논란", "영화진흥위원회 논란", 
                "대한체육회 논란", "국민체육진흥공단 논란", "게임물관리위원회 논란"
            ]
        }
        all_news = {}
        seen_titles = []
        seen_links = set()
        
        for cat, kws in categories.items():
            cat_items = []
            display_count = 30 # 쿼리가 구체적이므로 개수 조정 (20~30)
            
            # 모든 카테고리에 대해 지난 72시간 필터링 적용
            hours_limit = 72
            
            for kw in kws:
                news_items = self.fetch_news(kw, display=display_count)
                for item in news_items:
                    link = item.get("originallink", item.get("link", ""))
                    title = item.get("title", "")
                    description = item.get("description", "")
                    
                    # 0. 노이즈 필터링 (부정 키워드 포함 시 제거)
                    # 단, 제목이나 설명에 포함된 경우 스킵
                    is_noise = False
                    for nw in NOT_WORDS:
                        if nw in title or nw in description:
                            is_noise = True
                            break
                    if is_noise:
                        continue

                    # 1. URL 중복 체크 (Global)
                    if link in seen_links:
                        continue
                        
                    # 2. 제목 유사도 체크 (Global) - 의미없이 비슷한 기사 제거
                    is_dup = False
                    for seen_title in seen_titles:
                        if self.is_similar(title, seen_title):
                            is_dup = True
                            break
                    if is_dup:
                        continue

                    pub_date_str = item.get("pubDate")
                    if pub_date_str:
                        try:
                            pub_date = parsedate_to_datetime(pub_date_str)
                            if now - pub_date > timedelta(hours=hours_limit):
                                continue
                        except:
                            continue  # 날짜 파싱 실패 시 건너뜀 (안전 장치)
                            
                    seen_links.add(link)
                    seen_titles.append(title)
                    
                    cat_items.append({
                        "title": title,
                        "description": item.get("description", ""),
                        "link": link
                    })
            all_news[cat] = cat_items
            
        return all_news

if __name__ == "__main__":
    crawler = NewsCrawler()
    results = crawler.get_daily_reports()
    for kw, items in results.items():
        print(f"Keyword: {kw}, Found: {len(items)} items")
