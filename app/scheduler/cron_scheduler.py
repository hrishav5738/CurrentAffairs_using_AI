from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import traceback

def scheduled_pipeline_run():
    """Wrapper to run the daily pipeline with logging and crash-proofing."""
    print("\n⏰ [Scheduler] Triggering Automated Daily Current Affairs Pipeline (8:00 AM)...")
    try:
        from main import run_pipeline
        run_pipeline()
        print("✅ [Scheduler] Automated Daily Pipeline Execution Completed Successfully.")
    except Exception as e:
        print(f"❌ [Scheduler] Error during automated pipeline execution: {e}")
        traceback.print_exc()


def start_scheduler():
    """
    Initializes and starts the background daily scheduler.
    Runs once daily at 8:00 AM.
    """
    try:
        scheduler = BackgroundScheduler()
        
        # Configure a daily cron trigger at 8:00 AM
        trigger = CronTrigger(hour=8, minute=0)
        
        scheduler.add_job(
            scheduled_pipeline_run,
            trigger=trigger,
            id="daily_upsc_fetch",
            name="Daily UPSC Current Affairs Sync at 8:00 AM",
            replace_existing=True
        )
        
        scheduler.start()
        print("⏰ [Scheduler] Background Cron Job Active: Scheduled to run daily at 8:00 AM.")
        return scheduler
    except Exception as e:
        print(f"❌ [Scheduler] Failed to start Background Scheduler: {e}")
        return None
