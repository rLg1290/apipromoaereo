import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import threading

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models import Promotion
from app.storage import Storage
from app.telegram_client import fetch_history, listen_new_messages, stop_client


storage = Storage()
_listener_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed database with message history
    print("Fetching Telegram message history...")
    try:
        promos = await fetch_history(limit=500)
        saved = storage.save_many(promos)
        print(f"Seeded {saved} promotions from history.")
    except Exception as e:
        print(f"Warning: could not fetch history: {e}")

    # Start real-time listener in background
    global _listener_task
    _listener_task = asyncio.create_task(listen_new_messages(storage))

    yield

    # Shutdown
    if _listener_task:
        _listener_task.cancel()
    await stop_client()


app = FastAPI(
    title="API Promo Milhas",
    description="Coleta e organiza promoções de viagens em milhas do Telegram.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/promotions", response_model=list[Promotion], summary="Listar promoções")
async def list_promotions(
    destination: Optional[str] = Query(None, description="Filtrar por destino (parcial)"),
    airline: Optional[str] = Query(None, description="Filtrar por companhia aérea"),
    program: Optional[str] = Query(None, description="Filtrar por programa de milhas"),
    max_miles: Optional[int] = Query(None, description="Milhas máximas por trecho"),
    origin_code: Optional[str] = Query(None, description="Código IATA de origem (ex: NVT)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return storage.get_all(
        destination=destination,
        airline=airline,
        program=program,
        max_miles=max_miles,
        origin_code=origin_code,
        limit=limit,
        offset=offset,
    )


@app.get("/promotions/{promo_id}", response_model=Promotion, summary="Buscar promoção por ID")
async def get_promotion(promo_id: int):
    promo = storage.get_by_id(promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoção não encontrada.")
    return promo


@app.post("/sync", summary="Sincronizar histórico do Telegram manualmente")
async def sync_history(limit: int = Query(200, ge=1, le=1000)):
    """Busca as últimas mensagens do grupo e salva novas promoções."""
    try:
        promos = await fetch_history(limit=limit)
        saved = storage.save_many(promos)
        return {"fetched": len(promos), "saved": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", summary="Estatísticas do banco de dados")
async def stats():
    total = storage.count()
    all_promos = storage.get_all(limit=10_000)
    airlines = {}
    programs = {}
    destinations = {}
    for p in all_promos:
        airlines[p.airline] = airlines.get(p.airline, 0) + 1
        programs[p.program] = programs.get(p.program, 0) + 1
        destinations[p.destination] = destinations.get(p.destination, 0) + 1

    return {
        "total_promotions": total,
        "airlines": airlines,
        "programs": programs,
        "top_destinations": dict(sorted(destinations.items(), key=lambda x: x[1], reverse=True)[:10]),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "promotions_stored": storage.count()}
