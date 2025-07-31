"""
Scheduler Status API Endpoints

Provides endpoints to monitor background job status and manually trigger jobs.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from typing import Dict, Any

from app.core.scheduler import scheduler
from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.schemas.common import DataResponse, ErrorResponse

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def get_cron_service() -> RolledOptionsCronService:
    """Dependency to get cron service instance"""
    return RolledOptionsCronService()


@router.get(
    "/status",
    response_model=DataResponse,
    responses={
        200: {"description": "Scheduler status retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_scheduler_status():
    """
    Get status of background scheduler and all jobs
    
    Returns information about:
    - Scheduler state (running/stopped)
    - List of scheduled jobs with next run times
    - Overall system health
    """
    try:
        job_status = scheduler.get_job_status()
        
        return DataResponse(data={
            "scheduler": job_status,
            "system_health": "healthy" if job_status["status"] == "running" else "degraded",
            "message": "Background processing is active" if job_status["status"] == "running" else "Background processing is not running"
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


@router.post(
    "/trigger/rolled-options",
    response_model=DataResponse,
    responses={
        200: {"description": "Job triggered successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def trigger_rolled_options_job():
    """
    Manually trigger the rolled options background processing job
    
    This endpoint allows administrators to manually start the rolled options
    processing job without waiting for the scheduled time.
    """
    try:
        result = await scheduler.trigger_rolled_options_job()
        
        if result["success"]:
            return DataResponse(data={
                "message": result["message"],
                "triggered_at": "now",
                "estimated_completion": "2-5 minutes"
            })
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger job: {str(e)}"
        )


@router.get(
    "/processing-summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Processing summary retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_processing_summary(
    cron_service: RolledOptionsCronService = Depends(get_cron_service)
):
    """
    Get summary of rolled options processing across all users
    
    Returns:
    - Total users processed
    - Success/error statistics
    - Total chains detected
    - Last processing time
    """
    try:
        # Get overall processing status
        summary = await cron_service.get_processing_status()
        
        return DataResponse(data=summary)
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing summary: {str(e)}"
        )


@router.get(
    "/detailed-status",
    response_model=DataResponse,
    responses={
        200: {"description": "Detailed processing status retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_detailed_processing_status(
    cron_service: RolledOptionsCronService = Depends(get_cron_service)
):
    """
    Get detailed processing status including per-user information
    
    Returns:
    - Overall system health
    - Per-user processing status
    - Job execution history
    - Performance metrics
    """
    try:
        # Get scheduler status
        scheduler_status = scheduler.get_job_status()
        
        # Get overall processing summary
        overall_summary = await cron_service.get_processing_status()
        
        # Get recent job executions
        job_history = await scheduler.get_recent_job_logs(limit=10)
        
        return DataResponse(data={
            "system_health": {
                "scheduler_running": scheduler_status["status"] == "running",
                "jobs_count": len(scheduler_status["jobs"]),
                "next_run": scheduler_status["jobs"][0]["next_run"] if scheduler_status["jobs"] else None
            },
            "processing_summary": overall_summary,
            "performance_metrics": {
                "avg_processing_time": sum(log.get('duration_seconds', 0) for log in job_history) / max(len(job_history), 1),
                "success_rate": sum(1 for log in job_history if log.get('status') == 'success') / max(len(job_history), 1) * 100,
                "last_24h_jobs": len([log for log in job_history if log.get('started_at')]),
                "total_users_processed": sum(log.get('users_processed', 0) for log in job_history),
                "total_chains_processed": sum(log.get('chains_processed', 0) for log in job_history)
            },
            "job_history": job_history
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detailed status: {str(e)}"
        )