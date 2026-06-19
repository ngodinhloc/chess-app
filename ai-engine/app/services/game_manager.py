from fastapi import HTTPException
from app.routers.contracts.game_interface import GameInterface, GameMove, Actor


class GameManager:
    def __init__(self, redis):
        self._redis = redis

    def _key(self, game_uuid: str) -> str:
        return f"game:{game_uuid}"

    async def load(self, game_uuid: str) -> GameInterface:
        raw = await self._redis.get(self._key(game_uuid))
        if not raw:
            raise HTTPException(status_code=404, detail=f"Game {game_uuid} not found")
        return GameInterface.model_validate_json(raw)

    async def save(self, game_uuid: str, game: GameInterface) -> None:
        await self._redis.set(self._key(game_uuid), game.model_dump_json())

    async def append_move(self, game_uuid: str, game: GameInterface, move: GameMove) -> None:
        game.moves.append(move)
        await self.save(game_uuid, game)

    @staticmethod
    def update_move_message(game: GameInterface, order: int, actor: Actor, message: str) -> None:
        for move in reversed(game.moves):
            if move.order == order and move.actor == actor:
                move.message = message
                return
