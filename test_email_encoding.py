from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

kst = timezone(timedelta(hours=9))
now_date = datetime.now(kst).strftime('%Y-%m-%d')
# Replicate exact Subject line format
subject = f"[{now_date} {datetime.now(kst).strftime('%H:%M')}] 문체위 현안 심층 분석 보고서 (TOP 20)"

msg = MIMEMultipart()
msg['From'] = "sender@example.com"
msg['To'] = "receiver@example.com"
msg['Subject'] = subject
# Use body with utf-8 to ensure body is not the issue
msg.attach(MIMEText("Body with Korean: 안녕하세요", 'html', 'utf-8'))

print(f"Subject: {subject}")
print(f"Subject length: {len(subject)}")

try:
    s = msg.as_string()
    # Check if headers are encoded
    lines = s.splitlines()
    for line in lines:
        if line.startswith("Subject:"):
            print(f"Actual Header: {line}")
            # If it contains raw unicode, sendmail might fail
            try:
                line.encode('ascii')
                print("Header is ASCII-safe")
            except UnicodeEncodeError:
                print("Header is NOT ASCII-safe (contains raw unicode)")
                # Raising error to mimic sendmail behavior
                raise Exception("Header contains raw unicode, sendmail will fail")
except Exception as e:
    print(f"Failed: {e}")

# Fix with Header
from email.header import Header
print("\nTrying with Header()...")
msg2 = MIMEMultipart()
msg2['From'] = "sender@example.com"
msg2['To'] = "receiver@example.com"
msg2['Subject'] = Header(subject, 'utf-8')
msg2.attach(MIMEText("Body", 'html', 'utf-8'))

try:
    s2 = msg2.as_string()
    lines = s2.splitlines()
    for line in lines:
        if line.startswith("Subject:"):
            print(f"Fixed Header: {line}")
            line.encode('ascii')
            print("Fixed Header is ASCII-safe")
except Exception as e:
    print(f"Failed with Header: {e}")
