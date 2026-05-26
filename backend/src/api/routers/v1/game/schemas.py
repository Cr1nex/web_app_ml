from pydantic import BaseModel, Field


class ScoreSubmit(BaseModel):
    score: int = Field(ge=0, description="Final game score (non-negative integer)")
    game_name: str = Field(default="snake", max_length=50)


class LeaderboardEntry(BaseModel):
    username: str
    score: int
    played_at: str


class LeaderboardResponse(BaseModel):
    game: str
    entries: list[LeaderboardEntry]
