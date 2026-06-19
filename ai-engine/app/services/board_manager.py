import chess
from app.routers.contracts.game_interface import GameMove, Actor


class BoardManager:
    def build(self, moves: list[GameMove], skip_user_order: int | None = None) -> chess.Board:
        board = chess.Board()
        for move in moves:
            if not move.notation:
                continue
            if skip_user_order is not None and move.actor == Actor.user and move.order == skip_user_order:
                continue
            try:
                board.push_san(move.notation)
            except Exception:
                pass
        return board

    def apply_move(self, board: chess.Board, notation: str) -> bool:
        try:
            board.push_san(notation)
            return True
        except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError):
            return False
