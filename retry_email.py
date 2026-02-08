from email_sender import EmailSender
import os

def retry_email():
    report_path = "latest_report.md"
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found.")
        return

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        
        print(f"Read {len(report_content)} characters from {report_path}")
        
        sender = EmailSender()
        print("Attempting to send email...")
        if sender.send_report(report_content):
            print("✅ Email sent successfully!")
        else:
            print("❌ Failed to send email.")
            
    except Exception as e:
        print(f"Error during retry: {e}")

if __name__ == "__main__":
    retry_email()
