import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import markdown

load_dotenv()

class EmailSender:
    def __init__(self):
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.receivers = os.getenv("EMAIL_RECEIVERS").split(",")

    def send_report(self, report_content):
        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = ", ".join(self.receivers)
        from datetime import datetime, timedelta, timezone
        kst = timezone(timedelta(hours=9))
        now_date = datetime.now(kst).strftime('%Y-%m-%d')
        
        msg['Subject'] = f"[{now_date} {datetime.now(kst).strftime('%H:%M')}] 문체위 현안 심층 분석 보고서 (TOP 10)"

        # 마크다운을 HTML로 변환 (표 지원 및 개행 처리)
        html_report = markdown.markdown(report_content, extensions=['tables', 'nl2br'])

        # HTML 바디 생성 (고가독성 미니멀 프리미엄 디자인 - 인라인 스타일 강화)
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.7; color: #333; background-color: #f4f7f6; margin: 0; padding: 20px 10px; }}
                .container {{ max-width: 800px; margin: auto; background-color: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); overflow-wrap: break-word; }}
                
                /* Responsive Padding & Font Size for Mobile */
                @media only screen and (max-width: 600px) {{
                    body {{ padding: 10px 5px !important; }}
                    .container {{ padding: 25px 15px !important; border-radius: 8px !important; }}
                    h1 {{ font-size: 22px !important; margin-bottom: 25px !important; }}
                    h2 {{ font-size: 19px !important; padding: 10px 15px !important; }}
                    h3 {{ font-size: 17px !important; }}
                    p, li {{ font-size: 15px !important; line-height: 1.6 !important; letter-spacing: -0.02em !important; }}
                }}

                /* Title & Header */
                h1 {{ color: #1a2a6c; font-size: 32px; border-bottom: 4px solid #1a2a6c; padding-bottom: 20px; text-align: center; margin-bottom: 50px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.3; }}
                h2 {{ color: #1a2a6c; font-size: 24px; margin-top: 60px; margin-bottom: 30px; border-left: 8px solid #1a2a6c; padding: 12px 20px; background: #eef2f3; border-radius: 0 6px 6px 0; font-weight: 700; line-height: 1.4; }}
                h3 {{ color: #1a2a6c; font-size: 22px; margin-top: 50px; border-bottom: 3px solid #e1e8ed; padding-bottom: 15px; font-weight: 800; letter-spacing: -0.5px; }}
                
                /* Body Text - 모바일 단어 간격 강제 최적화 */
                p {{ margin-bottom: 28px; line-height: 1.8; text-align: left !important; word-break: keep-all; font-size: 16px; color: #444; letter-spacing: -0.01em; }}
                ul, ol {{ padding-left: 20px; margin-bottom: 30px; }}
                li {{ margin-bottom: 24px; font-size: 16px; color: #444; text-align: left !important; letter-spacing: -0.01em; }}
                strong {{ color: #000; font-weight: 700; }}
                
                /* Highlights & Boxes */
                blockquote {{ border-left: 4px solid #cbd5e0; padding-left: 20px; color: #4a5568; font-style: italic; margin: 35px 0; background-color: #f8fafc; padding: 15px 20px; border-radius: 0 8px 8px 0; }}
                
                /* Footnote (Direct Link Style) */
                sup {{ vertical-align: baseline; position: relative; top: -0.4em; font-weight: bold; }}
                sup a {{ color: #e53e3e; text-decoration: none; font-size: 11px; padding: 1px 4px; border-radius: 4px; background-color: #fff5f5; border: 1px solid #feb2b2; transition: all 0.2s; white-space: nowrap; }}
                
                .footer {{ font-size: 13px; color: #718096; text-align: center; margin-top: 80px; padding-top: 30px; border-top: 2px solid #edf2f7; line-height: 1.6; }}
                .disclaimer {{ font-size: 11px; color: #a0aec0; margin-top: 10px; letter-spacing: 0.2px; }}

                /* 전역 좌측 정렬 강제 (양끝 정렬 원천 차단) */
                .report-body * {{ text-align: left !important; word-break: normal !important; }}
            </style>
        </head>
        <body style="margin: 0; padding: 20px 10px; background-color: #f4f7f6; font-family: -apple-system, sans-serif;">
            <div class="container" style="max-width: 800px; margin: auto; background-color: #ffffff; padding: 40px; border-radius: 12px; text-align: left !important;">
                <h1 style="color: #1a2a6c; text-align: center; margin-bottom: 40px;">문체위 현안 심층 분석 보고서 (TOP 10)</h1>
                <div class="report-body" style="text-align: left !important;">
                    {html_report}
                </div>
                <div class="footer" style="text-align: center !important;">
                    <div>본 보고서는 AI 분석을 통해 작성된 문체위 현안 심층 리포트입니다.</div>
                    <div class="disclaimer">© 2026 Culture Sports Tourism Policy Monitor. All rights reserved.</div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, self.receivers, msg.as_string())
            print("Email sent successfully!")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
