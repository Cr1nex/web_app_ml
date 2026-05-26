import uuid
from core.db.session import SessionLocal
from core.db.models import RequestLog


class RequestLogRepo:
    @staticmethod
    def bulk_insert_logs(payloads: list[dict]):
        db = SessionLocal()
        try:
            for p in payloads:
                log_entry = RequestLog(
                    request_id=p.get("request_id") or str(uuid.uuid4()),
                    user_id=p.get("user_id"),
                    method=p.get("method", ""),
                    path=p.get("path", ""),
                    status_code=p.get("status_code", 0),
                    duration_ms=p.get("duration_ms", 0),
                    client_host=p.get("client_host")
                )
                db.merge(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
