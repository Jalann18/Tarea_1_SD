"""
main.py - Sistema de Caché (Cache Service)
Intercepta todas las consultas, verifica si existe en Redis (HIT) o
las delega al Generador de Respuestas (MISS), almacena el resultado
y registra el evento de métricas.
"""
import os
import json
import time
import hashlib
import httpx
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# -------------------------------------------------------------------------
# Configuración
# -------------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
RESPONSE_GEN_URL = os.getenv("RESPONSE_GEN_URL", "http://localhost:8001")
METRICS_URL = os.getenv("METRICS_URL", "http://localhost:8003")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

app = FastAPI(title="Cache Service", version="1.0")

# Clientes HTTP
redis_client: redis.Redis = None
http_client: httpx.AsyncClient = None


@app.on_event("startup")
async def startup():
    global redis_client, http_client
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    http_client = httpx.AsyncClient(timeout=30.0)
    # Verificar conexión
    redis_client.ping()
    print(f"Conectado a Redis en {REDIS_HOST}:{REDIS_PORT}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.aclose()


# -------------------------------------------------------------------------
# Generación de Cache Key según especificación de la tarea
# -------------------------------------------------------------------------
def build_cache_key(query_type: str, zone_id: str, zone_id_b: Optional[str],
                    confidence_min: float, bins: int) -> str:
    if query_type == "Q1":
        return f"count:{zone_id}:conf={confidence_min}"
    elif query_type == "Q2":
        return f"area:{zone_id}:conf={confidence_min}"
    elif query_type == "Q3":
        return f"density:{zone_id}:conf={confidence_min}"
    elif query_type == "Q4":
        return f"compare:density:{zone_id}:{zone_id_b}:conf={confidence_min}"
    elif query_type == "Q5":
        return f"confidence_dist:{zone_id}:bins={bins}"
    else:
        # Fallback genérico con hash
        raw = f"{query_type}:{zone_id}:{zone_id_b}:{confidence_min}:{bins}"
        return hashlib.md5(raw.encode()).hexdigest()


# -------------------------------------------------------------------------
# Modelos
# -------------------------------------------------------------------------
class QueryRequest(BaseModel):
    zone_id: str
    query_type: str
    confidence_min: Optional[float] = 0.0
    bins: Optional[int] = 5
    zone_id_b: Optional[str] = None


class QueryResponse(BaseModel):
    result: dict
    cache_hit: bool
    cache_key: str
    latency_ms: float


# -------------------------------------------------------------------------
# Endpoint principal
# -------------------------------------------------------------------------
@app.get("/health")
def health():
    try:
        redis_client.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "error"
    return {"status": "ok", "redis": redis_status}


@app.post("/query", response_model=QueryResponse)
async def handle_query(req: QueryRequest):
    t_start = time.time()

    cache_key = build_cache_key(
        req.query_type, req.zone_id, req.zone_id_b,
        req.confidence_min, req.bins
    )

    # ---- Intentar HIT en caché ----
    cached = redis_client.get(cache_key)
    if cached is not None:
        result = json.loads(cached)
        latency_ms = (time.time() - t_start) * 1000
        await send_metric("hit", req.query_type, req.zone_id, cache_key, latency_ms)
        return QueryResponse(
            result=result,
            cache_hit=True,
            cache_key=cache_key,
            latency_ms=round(latency_ms, 3),
        )

    # ---- MISS: delegar al Generador de Respuestas ----
    try:
        resp = await http_client.post(
            f"{RESPONSE_GEN_URL}/query",
            json=req.model_dump(),
        )
        resp.raise_for_status()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error al contactar al Generador de Respuestas: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    response_data = resp.json()
    result = response_data["result"]

    # ---- Almacenar en caché con TTL ----
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))

    latency_ms = (time.time() - t_start) * 1000
    await send_metric("miss", req.query_type, req.zone_id, cache_key, latency_ms)

    return QueryResponse(
        result=result,
        cache_hit=False,
        cache_key=cache_key,
        latency_ms=round(latency_ms, 3),
    )


@app.get("/stats")
def get_redis_stats():
    """Retorna estadísticas internas de Redis (hits, misses, evictions)."""
    info = redis_client.info("stats")
    memory = redis_client.info("memory")
    return {
        "keyspace_hits": info.get("keyspace_hits", 0),
        "keyspace_misses": info.get("keyspace_misses", 0),
        "evicted_keys": info.get("evicted_keys", 0),
        "used_memory_human": memory.get("used_memory_human", "N/A"),
        "maxmemory_human": memory.get("maxmemory_human", "N/A"),
        "maxmemory_policy": memory.get("maxmemory_policy", "N/A"),
    }


# -------------------------------------------------------------------------
# Envío de métricas (non-blocking, best-effort)
# -------------------------------------------------------------------------
async def send_metric(event_type: str, query_type: str, zone_id: str, cache_key: str, latency_ms: float):
    try:
        await http_client.post(
            f"{METRICS_URL}/event",
            json={
                "event_type": event_type,
                "query_type": query_type,
                "zone_id": zone_id,
                "cache_key": cache_key,
                "latency_ms": latency_ms,
                "timestamp": time.time(),
            },
            timeout=2.0,
        )
    except Exception:
        pass  # Las métricas no deben bloquear las consultas
