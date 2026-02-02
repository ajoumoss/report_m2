from news_crawler import NewsCrawler
from llm_processor import LLMProcessor
from email_sender import EmailSender
from email_sender import EmailSender
import sys
import json
from datetime import datetime

def main():
    try:
        print("1. 뉴스 수집 시작...")
        crawler = NewsCrawler()
        news_data = crawler.get_daily_reports()
        
        # 데이터가 있는지 확인
        total_items = sum(len(items) for items in news_data.values())
        if total_items == 0:
            print("수집된 뉴스가 없습니다. 종료합니다.")
            return

        print(f"2. AI 분석 시작 (총 {total_items}건)...")
        processor = LLMProcessor()
        report_content = processor.generate_report(news_data)

        print("3. 이메일 발송 시작...")
        sender = EmailSender()
        if sender.send_report(report_content):
            print("전체 프로세스가 성공적으로 완료되었습니다.")
        else:
            print("이메일 발송에 실패했습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
