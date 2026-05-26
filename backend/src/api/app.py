import redis
import uvicorn
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routers.v1.routes import api_router
from core.configs.settings import settings
from core.middleware.rabbitmq_logger import RabbitMQLogger, RabbitMQLoggingMiddleware
from core.middleware.request_id import RequestIdMiddleware
from core.rate_limit import limiter
from services.nightly_jobs import setup_nightly_jobs





app = FastAPI(
	title=settings.app_name,
	docs_url="/api/docs",
	redoc_url="/api/redoc",
	openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RabbitMQLoggingMiddleware)
app.include_router(api_router, prefix=settings.api_v1_prefix)

@app.on_event("startup")
async def startup():
	app.state.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
	app.state.rabbitmq_logger = RabbitMQLogger(settings.rabbitmq_url)
	try:
		await app.state.rabbitmq_logger.connect()
	except Exception as exc:
		print(f"WARNING: RabbitMQ unavailable at startup ({exc}). Request logging disabled until reconnect.")

	app.state.scheduler = setup_nightly_jobs(app)

@app.on_event("shutdown")
async def shutdown():
	scheduler = getattr(app.state, "scheduler", None)
	if scheduler:
		scheduler.shutdown()
	rabbit = getattr(app.state, "rabbitmq_logger", None)
	if rabbit:
		await rabbit.close()
	redis_client = getattr(app.state, "redis", None)
	if redis_client:
		redis_client.close()

@app.get("/health")
def health():
	return {"status": "ok"}


if __name__ == "__main__":
	uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=False)
