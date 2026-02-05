from news_crawler import NewsCrawler
from llm_processor import LLMProcessor
from email_sender import EmailSender
from report_history_manager import ReportHistoryManager
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

        print("2. 최근 보고서 이력 조회...")
        history_manager = ReportHistoryManager()
        recent_reports = history_manager.get_recent_reports(limit=3)
        print(f"   - 최근 {len(recent_reports)}개의 보고서를 참조하여 중복을 방지합니다.")

        print(f"3. AI 분석 시작 (총 {total_items}건)...")
        processor = LLMProcessor()
        # 최근 보고서 이력 전달
        report_content = processor.generate_report(news_data, previous_reports=recent_reports)

        print("4. 이메일 발송 시작...")
        
        # 검증을 위해 로컬 파일로 저장
        with open("latest_report.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        print("✅ 최신 보고서가 'latest_report.md'로 저장되었습니다.")
        
        # 히스토리에 저장
        history_manager.save_report(report_content)

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
