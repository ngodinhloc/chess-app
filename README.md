# Chess Engine

An AI-powered chess game where you play against Claude at three skill levels. You play as White via a drag-and-drop board. After each move, Claude picks a legal reply and writes natural-language commentary in the chat panel. Move quality and commentary style both adapt to the engine level — Amateur blunders occasionally and narrates its own reasoning; Professional plays sharply and responds analytically. Games are persisted so history can be replayed move by move, with commentary preserved alongside each position.

---

## Screenshots

**Game setup — history sidebar, engine level selector, greyed-out board**

The left sidebar lists previous games with level badges and move counts. The level dropdown shows Amateur / Intermediate / Professional. The board and move list are greyed out until Start is clicked.

![Game setup with history sidebar and level selector open](./screenshot_1.png)

**Professional-level game in progress — Thinking… indicator and analytical commentary**

The amber "Thinking…" badge appears while Claude is processing. The move list tracks the game. The chat panel shows terse, analytical commentary — explaining opening theory and strategic ideas rather than narrating the move.

![Professional game with Thinking indicator and analytical commentary in chat](./screenshot_2.png)

**Amateur-level game — casual commentary and full move history**

The same game captured in `moves.json`: Ken vs Amateur Engine, Polish Opening (1.b4). The engine's commentary is casual and emoji-filled — celebrating material grabs, admitting it might be missing something, and cheering the opponent on.

![Amateur game with Polish Opening and casual emoji commentary](./screenshot_3.png)

---

## Architecture

![Architecture diagram](./architecture.png)

**Frontend** (React + Vite, port 3000) — drag-and-drop board, move list, and chat panel. Polls `GET /api/game/{id}` every 2 s during play to pick up the engine's reply, and supports ply-by-ply replay of completed games.

**Backend** (NestJS, port 8000) — REST API:
- `POST /api/game/new` — create game in PostgreSQL + Redis, fire greeting to AI Engine
- `POST /api/game/:id/move` — append user move to Redis, fire-and-forget to AI Engine (returns 202)
- `POST /api/game/:id/stop` — persist full move array to PostgreSQL, delete Redis key
- `GET /api/game/:id` — return live game from Redis, or persisted game from PostgreSQL
- `GET /api/game/history` — return last 50 games from PostgreSQL

**AI Engine** (FastAPI + LangGraph, port 8001) — loads the current game from Redis, validates the user's move with `python-chess`, then invokes Claude (`claude-sonnet-4-6`) with the current FEN, legal moves, and engine level. Claude returns a single JSON object with `notation` (the chosen move in SAN) and `message` (natural-language commentary). The engine appends the agent move to the game and writes it back to Redis.

**Redis** — live game state during play, keyed by `game:{uuid}`; shared by the backend and AI Engine so no inter-service polling is needed.

**PostgreSQL** — persistent store; written once when a game starts (empty) and again when it stops (full move array). All history and replay reads come from here.

---

## Services

| Service | Port | Directory | Stack |
|---------|------|-----------|-------|
| postgres | 5432 | — | PostgreSQL 17 |
| redis | 6379 | — | Redis 7 |
| ai-engine | 8001 | `ai-engine/` | FastAPI + LangGraph + python-chess |
| backend | 8000 | `backend/` | NestJS 11 + TypeORM |
| frontend | 3000 | `frontend/` | Vite + React 19 + Tailwind CSS 4 |

### Frontend (port 3000)

- Game setup form: username, engine level (Amateur / Intermediate / Professional), Start button
- Drag-and-drop board via `react-chessboard`; client-side FEN tracking with `chess.js`
- Polls `GET /api/game/{id}` every 2 seconds while the game is active
- Move list renders white/black pairs (`1. e4 e5`); in history view each half-move is clickable and replays the board at that ply
- Chat panel shows engine commentary alongside each move, tagged with a notation badge
- Collapsible history sidebar; New Game button always visible

### Backend (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/game/new` | Create game in PostgreSQL + Redis, trigger greeting, return `{ id }` |
| `POST` | `/api/game/:id/move` | Append user move to Redis, trigger AI Engine (202) |
| `POST` | `/api/game/:id/stop` | Persist moves to PostgreSQL, delete Redis key |
| `GET` | `/api/game/history` | Last 50 games from PostgreSQL |
| `GET` | `/api/game/:id` | Live game from Redis, or persisted game from PostgreSQL |
| `GET` | `/api/health` | Health check |

### AI Engine (port 8001)

Receives `POST /api/game/move` from the backend. Rebuilds the board by replaying all prior moves with `python-chess`, validates the user's move, then invokes Claude to pick a reply and write a comment. Both are stored together in the same `GameMove` record.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/game/move` | Validate move, run engine, append response to Redis |
| `GET` | `/api/health` | Health check |

---

## Data model

```
EngineLevel:  Amateur | Intermediate | Professional
Actor:        user    | agent
GameStatus:   active  | stopped

GameMove {
  actor:    Actor
  order:    number      // move pair number; 0 = greeting
  notation: string      // SAN; empty for greeting and game-over messages
  message:  string      // engine commentary or error text
}

GameInterface {
  id:          uuid
  userName:    string
  engineLevel: EngineLevel
  moves:       GameMove[]
  status:      GameStatus
  startedAt:   datetime
}
```

User and engine responses to the same move share the same `order` number. The greeting sits at `order: 0` with an empty `notation`. Filtering `notation && order > 0` gives the chess-move list for board replay.

---

## Quick start

```bash
# 1. Set the Anthropic API key
cp ai-engine/.env.example ai-engine/.env
# edit ai-engine/.env and set ANTHROPIC_API_KEY

# 2. Start all services
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

| Key | Where to get |
|-----|-------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
