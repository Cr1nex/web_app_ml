import asyncio
import json
import time

import aio_pika
from starlette.middleware.base import BaseHTTPMiddleware


class RabbitMQLogger:
    def __init__(self, url: str, queue_name: str = "request-logs"):
        self.url = url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None

    async def connect(self):
        retries = 5
        for i in range(retries):
            try:
                self.connection = await aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel()
                self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
                self.exchange = self.channel.default_exchange
                print(f"Successfully connected to RabbitMQ at {self.url}")
                return
            except Exception as e:
                if i < retries - 1:
                    print(f"RabbitMQ connection failed, retrying in 2s... ({e})")
                    await asyncio.sleep(2)
                else:
                    raise e

    async def publish(self, payload: dict):
        if not self.exchange:
            return
        body = json.dumps(payload).encode("utf-8")
        message = aio_pika.Message(body=body, content_type="application/json")
        await self.exchange.publish(message, routing_key=self.queue_name)

    async def close(self):
        if self.connection:
            await self.connection.close()

    async def drain_queue(self, batch_size: int = 1000):
        """Fetches up to batch_size messages from the queue without blocking."""
        if not self.queue:
            return [], []
        
        messages = []
        payloads = []
        try:
            while len(messages) < batch_size:
                msg = await self.queue.get(fail=False)
                if msg is None:
                    break
                messages.append(msg)
                try:
                    body = json.loads(msg.body.decode("utf-8"))
                    payloads.append(body)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error draining queue: {e}")
            
        return messages, payloads


class RabbitMQLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger = getattr(request.app.state, "rabbitmq_logger", None)
        payload = {
            "request_id": getattr(request.state, "request_id", None),
            "user_id": getattr(request.state, "user_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_host": request.client.host if request.client else None,
        }
        if logger:
            try:
                await logger.publish(payload)
            except Exception:
                pass
        return response
