from uuid import UUID

from repos.game_score_repo import GameScoreRepo


class GameScoreService:
    def __init__(self, db):
        self.repo = GameScoreRepo(db)

    def save_score(self, user_id: UUID, score: int, game_name: str = "snake"):
        return self.repo.create(user_id=user_id, score=score, game_name=game_name)

    def leaderboard(self, game_name: str = "snake", limit: int = 10) -> list[dict]:
        return self.repo.get_leaderboard(game_name=game_name, limit=limit)

    def user_best(self, user_id: UUID, game_name: str = "snake"):
        return self.repo.get_user_best(user_id=user_id, game_name=game_name)
