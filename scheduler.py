import schedule
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def run_digest_pipeline():
    """Run the full digest pipeline"""
    print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Starting scheduled digest run...")
    
    try:
        # Change to project directory
        project_dir = Path(__file__).parent
        
        # Run the pipeline
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "run"
        ], capture_output=True, text=True, cwd=project_dir)
        
        if result.returncode == 0:
            print("✅ Scheduled digest completed successfully")
            print("📧 Check output folder for new digest files")
        else:
            print("❌ Scheduled digest failed")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Scheduler error: {e}")

def main():
    """Main scheduler"""
    print("🕐 AI Digest Scheduler Starting...")
    print("📅 Scheduled to run daily at 8:00 AM")
    print("📁 Digests will be saved to the 'output' folder")
    
    # Schedule daily run at 8 AM
    schedule.every().day.at("08:00").do(run_digest_pipeline)
    
    # For testing, uncomment this line to run every 30 minutes
    # schedule.every(30).minutes.do(run_digest_pipeline)
    
    print("⏰ Scheduler running... Press Ctrl+C to stop")
    print("💡 Tip: Run 'python -m src.cli.main run' manually anytime")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped")

if __name__ == "__main__":
    main()