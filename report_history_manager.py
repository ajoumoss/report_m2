import os
import glob
from datetime import datetime

class ReportHistoryManager:
    def __init__(self, history_dir="history"):
        self.history_dir = history_dir
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def save_report(self, content):
        """
        Saves the provided report content to a file with a timestamp.
        Keeps only the latest 5 reports (buffer for safety, though 3 are used).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.md"
        filepath = os.path.join(self.history_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Report saved to history: {filepath}")
        
        self._cleanup_old_reports()

    def get_recent_reports(self, limit=3):
        """
        Returns a list of the content of the most recent 'limit' reports.
        """
        files = glob.glob(os.path.join(self.history_dir, "report_*.md"))
        # Sort by filename (which includes timestamp) descending
        files.sort(reverse=True)
        
        recent_files = files[:limit]
        reports = []
        for fpath in recent_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reports.append(f.read())
            except Exception as e:
                print(f"Error reading history file {fpath}: {e}")
                
        return reports

    def _cleanup_old_reports(self, keep_count=5):
        """
        Deletes old reports, keeping only the latest 'keep_count'.
        """
        files = glob.glob(os.path.join(self.history_dir, "report_*.md"))
        files.sort(reverse=True)
        
        if len(files) > keep_count:
            for fpath in files[keep_count:]:
                try:
                    os.remove(fpath)
                    print(f"🗑️ Old report removed: {fpath}")
                except Exception as e:
                    print(f"Error removing old report {fpath}: {e}")
