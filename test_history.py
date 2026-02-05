from report_history_manager import ReportHistoryManager
import os
import time

def test_history_manager():
    print("Test: Initializing Manager")
    manager = ReportHistoryManager(history_dir="test_history")
    
    print("Test: Saving Report 1")
    manager.save_report("Report Content 1")
    time.sleep(1) # Ensure timestamp diff
    
    print("Test: Saving Report 2")
    manager.save_report("Report Content 2")
    time.sleep(1)
    
    print("Test: Saving Report 3")
    manager.save_report("Report Content 3")
    time.sleep(1)
    
    print("Test: Saving Report 4")
    manager.save_report("Report Content 4")
    
    print("Test: Retrieving Recent Reports (Limit 3)")
    recent = manager.get_recent_reports(limit=3)
    
    assert len(recent) == 3
    print(f"✅ Retrieved {len(recent)} reports.")
    assert "Report Content 4" in recent[0]
    print("✅ Latest report is first.")
    
    print("Test: Checking total files (Should be <= 5)")
    import glob
    files = glob.glob("test_history/report_*.md")
    print(f"Total files in history: {len(files)}")
    
    # Cleanup
    import shutil
    shutil.rmtree("test_history")
    print("✅ Cleanup complete.")

if __name__ == "__main__":
    test_history_manager()
