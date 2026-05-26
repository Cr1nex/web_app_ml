from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from core.db.models import GameScore, User


class GameScoreRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: UUID, score: int, game_name: str = "snake") -> GameScore:
        entry = GameScore(user_id=user_id, score=score, game_name=game_name)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_leaderboard(self, game_name: str = "snake", limit: int = 10) -> list[dict]:
        stmt = (
            select(User.username, GameScore.score, GameScore.played_at)
            .join(User, GameScore.user_id == User.user_id)
            .where(GameScore.game_name == game_name)
            .order_by(desc(GameScore.score))
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {"username": r.username, "score": r.score, "played_at": r.played_at.isoformat()}
            for r in rows
        ]

    def get_user_best(self, user_id: UUID, game_name: str = "snake") -> GameScore | None:
        stmt = (
            select(GameScore)
            .where(GameScore.user_id == user_id, GameScore.game_name == game_name)
            .order_by(desc(GameScore.score))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
