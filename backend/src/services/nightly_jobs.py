import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from repos.request_log_repo import RequestLogRepo


async def process_nightly_logs(logger):
    if not logger:
        return
        
    total_processed = 0
    while True:
        messages, payloads = await logger.drain_queue(batch_size=1000)
        if not payloads and not messages:
            break
        try:
            if payloads:
                await asyncio.to_thread(RequestLogRepo.bulk_insert_logs, payloads)
            for msg in messages:
                await msg.ack()
            total_processed += len(payloads)
        except Exception as e:
            print(f"Failed to process a batch of nightly logs: {e}")
            break  # Stop processing if DB fails, to avoid data loss
            
    if total_processed > 0:
        print(f"Successfully processed and stored {total_processed} request logs.")


def setup_nightly_jobs(app) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    
    async def job_wrapper():
        logger = getattr(app.state, "rabbitmq_logger", None)
        await process_nightly_logs(logger)
        
    scheduler.add_job(job_wrapper, 'cron', hour=2, minute=0)
    scheduler.start()
    return scheduler
