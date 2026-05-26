from fastapi import APIRouter, BackgroundTasks, Request

from services.nightly_jobs import process_nightly_logs

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/drain-logs")
async def manual_drain_logs(request: Request, background_tasks: BackgroundTasks):
    """
    Manually trigger the log queue drain.
    Runs asynchronously in the background.
    """
    logger = getattr(request.app.state, "rabbitmq_logger", None)
    if not logger:
        return {"status": "error", "detail": "RabbitMQ logger not available"}
    
    background_tasks.add_task(process_nightly_logs, logger)
    
    return {"status": "queued", "detail": "Log draining started in the background."}
