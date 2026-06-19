import logging
from functools import cached_property
from app.agent.agent_graph import AgentGraph
from app.services.game_service import GameService
from app.services.game_manager import GameManager
from app.services.board_manager import BoardManager
from app.services.redis_client import RedisClient


class Container:
    def logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

    @cached_property
    def graph(self):
        return AgentGraph().build()

    @cached_property
    def redis(self):
        return RedisClient().get()

    @cached_property
    def game_manager(self) -> GameManager:
        return GameManager(redis=self.redis)

    @cached_property
    def board_manager(self) -> BoardManager:
        return BoardManager()

    @cached_property
    def game_service(self) -> GameService:
        return GameService(
            graph=self.graph,
            game_manager=self.game_manager,
            board_manager=self.board_manager,
            logger=self.logger("game_service"),
        )


container = Container()
