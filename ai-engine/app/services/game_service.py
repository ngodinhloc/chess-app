import logging
import chess
from app.routers.contracts.game_interface import GameInterface, GameMove, Actor, MoveRequest
from app.services.game_manager import GameManager
from app.services.board_manager import BoardManager


class GameService:
    def __init__(self, graph, game_manager: GameManager, board_manager: BoardManager, logger: logging.Logger):
        self._graph = graph
        self._game_manager = game_manager
        self._board_manager = board_manager
        self._logger = logger

    async def handle(self, request: MoveRequest) -> None:
        game = await self._game_manager.load(request.game_uuid)

        if request.order == 0:
            await self._send_greeting(request.game_uuid, game)
            return

        board = self._board_manager.build(game.moves, skip_user_order=request.order)

        if request.actor == Actor.user:
            if not self._board_manager.apply_move(board, request.notation):
                self._logger.warning("Illegal move %s for game %s", request.notation, request.game_uuid)
                self._game_manager.update_move_message(game, request.order, Actor.user, "That move is not legal. Try again!")
                await self._game_manager.save(request.game_uuid, game)
                return

        if board.is_game_over():
            await self._handle_game_over(request.game_uuid, game, board, request.order)
            return

        legal_moves = [board.san(m) for m in board.legal_moves]
        if not legal_moves:
            await self._handle_game_over(request.game_uuid, game, board, request.order)
            return

        result = await self._graph.ainvoke({
            "messages": [],
            "fen": board.fen(),
            "legal_moves": legal_moves,
            "engine_level": game.engineLevel,
            "notation": "",
            "message": "",
        })

        agent_notation = result.get("notation", "")
        agent_message = result.get("message", "Your move!")

        if agent_notation not in legal_moves:
            self._logger.warning(
                "LLM chose illegal move '%s', falling back to first legal move", agent_notation
            )
            agent_notation = legal_moves[0]

        agent_move = GameMove(
            actor=Actor.agent,
            order=request.order,
            notation=agent_notation,
            message=agent_message,
        )
        await self._game_manager.append_move(request.game_uuid, game, agent_move)

    async def _send_greeting(self, game_uuid: str, game: GameInterface) -> None:
        greeting = GameMove(
            actor=Actor.agent,
            order=0,
            notation="",
            message=(
                f"Welcome, {game.userName}! I'm your chess opponent at {game.engineLevel} level. "
                "You play as White — make your first move!"
            ),
        )
        await self._game_manager.append_move(game_uuid, game, greeting)

    async def _handle_game_over(
        self, game_uuid: str, game: GameInterface, board: chess.Board, order: int
    ) -> None:
        if board.is_checkmate():
            message = "Checkmate! Well played!"
        elif board.is_stalemate():
            message = "Stalemate — it's a draw!"
        elif board.is_insufficient_material():
            message = "Draw by insufficient material."
        else:
            message = "Game over!"

        agent_move = GameMove(actor=Actor.agent, order=order, notation="", message=message)
        await self._game_manager.append_move(game_uuid, game, agent_move)
