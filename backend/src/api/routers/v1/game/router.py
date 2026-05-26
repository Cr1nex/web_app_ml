from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from api.routers.v1.game.schemas import LeaderboardEntry, LeaderboardResponse, ScoreSubmit
from core.db.session import get_db
from core.utils.deps import get_current_user_id
from services.game_score_service import GameScoreService

router = APIRouter(prefix="/game", tags=["game"])


def get_service(db=Depends(get_db)) -> GameScoreService:
    return GameScoreService(db)


@router.post("/scores", status_code=201)
def submit_score(
    payload: ScoreSubmit,
    user_id: UUID = Depends(get_current_user_id),
    service: GameScoreService = Depends(get_service),
):
    """Save a game score for the authenticated user."""
    service.save_score(user_id=user_id, score=payload.score, game_name=payload.game_name)
    return {"saved": True}


@router.get("/scores/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    game: str = Query(default="snake", max_length=50),
    limit: int = Query(default=10, ge=1, le=50),
    service: GameScoreService = Depends(get_service),
):
    """Return top scores for a game (public endpoint)."""
    entries = service.leaderboard(game_name=game, limit=limit)
    return LeaderboardResponse(
        game=game,
        entries=[LeaderboardEntry(**e) for e in entries],
    )
