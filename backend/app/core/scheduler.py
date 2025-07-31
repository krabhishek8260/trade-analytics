"""
Background Job Scheduler

Manages background processing jobs using APScheduler.
Handles rolled options processing and other periodic tasks.
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.models.job_execution_log import JobExecutionLog
from app.core.database import get_db

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Manages background job scheduling"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.cron_service = RolledOptionsCronService()
        self.is_running = False
    
    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            return
        
        try:
            # Create scheduler with asyncio executor
            self.scheduler = AsyncIOScheduler(
                timezone='UTC',
                job_defaults={
                    'coalesce': True,  # Combine multiple pending executions into one
                    'max_instances': 1,  # Only one instance of each job at a time
                    'misfire_grace_time': 300  # 5 minutes grace period
                }
            )
            
            # Add event listeners
            self.scheduler.add_listener(
                self._job_executed_listener, 
                EVENT_JOB_EXECUTED
            )
            self.scheduler.add_listener(
                self._job_error_listener, 
                EVENT_JOB_ERROR
            )
            
            # Schedule rolled options processing job
            self.scheduler.add_job(
                func=self._process_rolled_options_job,
                trigger=IntervalTrigger(minutes=30),  # Every 30 minutes
                id='rolled-options-processing',
                name='Rolled Options Background Processing',
                replace_existing=True
            )
            
            # Schedule daily cleanup job
            self.scheduler.add_job(
                func=self._daily_cleanup_job,
                trigger=CronTrigger(hour=2, minute=0),  # 2 AM UTC daily
                id='daily-cleanup',
                name='Daily Database Cleanup',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Background scheduler started successfully")
            logger.info(f"Scheduled jobs: {[job.id for job in self.scheduler.get_jobs()]}")
            
        except Exception as e:
            logger.error(f"Failed to start background scheduler: {str(e)}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the background scheduler"""
        if not self.is_running or not self.scheduler:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Background scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping background scheduler: {str(e)}", exc_info=True)
    
    async def _process_rolled_options_job(self):
        """Background job to process rolled options for all users"""
        job_start = datetime.now()
        logger.info("Starting rolled options background processing job")
        
        # Create job execution log entry
        log_entry = JobExecutionLog(
            job_name="rolled-options-processing",
            job_id="rolled-options-processing",
            started_at=job_start,
            triggered_manually=False
        )
        
        try:
            result = await self.cron_service.process_all_users()
            
            job_end = datetime.now()
            duration = (job_end - job_start).total_seconds()
            
            # Update log entry with results
            log_entry.completed_at = job_end
            log_entry.duration_seconds = duration
            log_entry.users_processed = result.get('users_processed', 0)
            log_entry.chains_processed = result.get('total_chains', 0)
            log_entry.orders_processed = result.get('orders_processed', 0)
            
            if result.get('success'):
                log_entry.status = 'success'
                logger.info(
                    f"Rolled options processing completed successfully: "
                    f"{result.get('users_processed', 0)} users, "
                    f"{result.get('total_chains', 0)} chains, "
                    f"{duration:.1f}s"
                )
            else:
                log_entry.status = 'error'
                log_entry.error_message = result.get('message', 'Unknown error')
                logger.error(
                    f"Rolled options processing failed: {result.get('message', 'Unknown error')}"
                )
            
            # Log any errors
            if result.get('errors'):
                logger.warning(f"Processing errors: {result['errors']}")
                
        except Exception as e:
            job_end = datetime.now()
            duration = (job_end - job_start).total_seconds()
            
            log_entry.completed_at = job_end
            log_entry.duration_seconds = duration
            log_entry.status = 'error'
            log_entry.error_message = str(e)
            
            logger.error(
                f"Rolled options background job failed after {duration:.1f}s: {str(e)}", 
                exc_info=True
            )
        
        finally:
            # Save log entry to database
            await self._save_job_log(log_entry)
    
    async def _daily_cleanup_job(self):
        """Daily cleanup job for database maintenance"""
        logger.info("Starting daily cleanup job")
        
        try:
            # Future: Add cleanup tasks here
            # - Remove old error logs
            # - Clean up stale cache entries
            # - Archive old processing records
            
            logger.info("Daily cleanup job completed successfully")
            
        except Exception as e:
            logger.error(f"Daily cleanup job failed: {str(e)}", exc_info=True)
    
    def _job_executed_listener(self, event):
        """Listener for successful job executions"""
        runtime = getattr(event, 'run_time', 0)
        logger.info(
            f"Job '{event.job_id}' executed successfully in {runtime:.2f}s"
        )
    
    def _job_error_listener(self, event):
        """Listener for job execution errors"""
        logger.error(
            f"Job '{event.job_id}' failed: {event.exception}",
            exc_info=event.traceback
        )
    
    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs"""
        if not self.scheduler:
            return {"status": "not_started", "jobs": []}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running" if self.is_running else "stopped",
            "jobs": jobs,
            "scheduler_state": str(self.scheduler.state) if self.scheduler else "none"
        }
    
    async def trigger_rolled_options_job(self) -> dict:
        """Manually trigger the rolled options processing job"""
        if not self.scheduler:
            return {"success": False, "message": "Scheduler not running"}
        
        try:
            # Run the job immediately
            job = self.scheduler.get_job('rolled-options-processing')
            if job:
                self.scheduler.modify_job(
                    'rolled-options-processing',
                    next_run_time=datetime.now()
                )
                logger.info("Manually triggered rolled options processing job")
                return {"success": True, "message": "Job triggered successfully"}
            else:
                return {"success": False, "message": "Job not found"}
                
        except Exception as e:
            logger.error(f"Error triggering job: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _save_job_log(self, log_entry: JobExecutionLog):
        """Save job execution log to database"""
        try:
            async for db in get_db():
                db.add(log_entry)
                await db.commit()
                logger.debug(f"Saved job execution log: {log_entry.job_name} - {log_entry.status}")
        except Exception as e:
            logger.error(f"Failed to save job execution log: {str(e)}", exc_info=True)
    
    async def get_recent_job_logs(self, limit: int = 10) -> List[dict]:
        """Get recent job execution logs"""
        try:
            async for db in get_db():
                from sqlalchemy import select, desc
                result = await db.execute(
                    select(JobExecutionLog)
                    .order_by(desc(JobExecutionLog.started_at))
                    .limit(limit)
                )
                logs = result.scalars().all()
                return [log.execution_summary for log in logs]
        except Exception as e:
            logger.error(f"Failed to get job logs: {str(e)}")
            return []


# Global scheduler instance
scheduler = BackgroundScheduler()