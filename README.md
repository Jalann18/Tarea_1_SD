# Tarea 1 SD - Plataforma de Análisis de Edificios (Google Open Buildings)

## Arquitectura

```
┌────────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│  Generador de  │───▶│  Cache Service  │───▶│  Response Generator  │
│    Tráfico     │    │   (FastAPI +    │    │   (FastAPI + Pandas  │
│   (FastAPI)    │    │     Redis)      │    │    + Dataset en RAM) │
└────────────────┘    └─────────────────┘    └──────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Metrics Storage  │
                    │ (FastAPI + CSV)  │
                    └──────────────────┘
```

## Stack Tecnológico

| Componente | Tecnología | Justificación |
|---|---|---|
| Servicios | Python 3.11 + FastAPI | Async nativo, tipado fuerte, documentación automática |
| Caché | Redis 7 | Soporte nativo TTL, políticas LRU/LFU/Random, comandos INFO |
| Dataset | Google Open Buildings v3 | Dataset real especificado en la tarea |
| Orquestación | Docker Compose | Requerido por la tarea, permite reproducibilidad |
| Análisis | Pandas + Matplotlib | Estándar científico en Python |

## Requisitos

- Docker Desktop instalado
- Docker Compose v2
- Python 3.11+ (solo para `run_experiments.py` y `analyze.py`)
- pip: `pip install httpx pandas matplotlib pyarrow`

## Ejecución Paso a Paso

### 1. Levantar todos los servicios

```bash
docker compose up -d
```

> ⚠️ La primera vez puede tomar 5-10 minutos porque descarga el dataset de Google Open Buildings.

### 2. Verificar que todo está activo

```bash
docker compose ps
docker compose logs response_generator | tail -20
```

### 3. Ejecutar un experimento rápido (manual)

```bash
# Desde tu navegador o curl: lanzar 200 requests con distribución Zipf
curl -X POST http://localhost:8004/run \
  -H "Content-Type: application/json" \
  -d '{"n_requests": 200, "distribution": "zipf"}'

# Ver estadísticas en tiempo real
curl http://localhost:8003/stats
```

### 4. Ejecutar TODOS los experimentos automáticamente

```bash
pip install httpx
python run_experiments.py
```

### 5. Generar gráficos para el informe

```bash
# Primero, copiar los datos de métricas del contenedor
docker cp metrics_storage:/metrics/events.csv results/events.csv
docker cp metrics_storage:/metrics/experiments.csv results/experiments.csv

pip install pandas matplotlib pyarrow
python analyze.py
```

Los gráficos quedan en `results/figures/`.

## Endpoints de los Servicios

| Servicio | Puerto | Documentación |
|---|---|---|
| Response Generator | 8001 | http://localhost:8001/docs |
| Cache Service | 8002 | http://localhost:8002/docs |
| Metrics Storage | 8003 | http://localhost:8003/docs |
| Traffic Generator | 8004 | http://localhost:8004/docs |

## Experimentos Implementados

1. **Distribución de Tráfico**: Zipf (α=1.5) vs. Uniforme
2. **Políticas de Evicción**: LRU vs. LFU vs. Random (FIFO aprox.)
3. **Tamaño de Caché**: 50MB vs. 200MB vs. 500MB
4. **TTL**: 60s vs. 300s vs. 3600s

## Variables de Configuración (.env)

| Variable | Default | Descripción |
|---|---|---|
| `CACHE_MAX_MEMORY` | `200mb` | Memoria máxima de Redis |
| `CACHE_EVICTION_POLICY` | `allkeys-lru` | Política de evicción |
| `CACHE_TTL` | `300` | TTL en segundos |
| `PROCESSING_DELAY_MS` | `100` | Delay simulado en Response Generator |
| `DISTRIBUTION` | `zipf` | Distribución del Traffic Generator |
| `N_REQUESTS` | `1000` | Número de requests por experimento |
| `ZIPF_ALPHA` | `1.5` | Parámetro α de la distribución Zipf |
| `REQUEST_RATE` | `10` | Requests por segundo |

## Estructura del Proyecto

```
Tarea 1 SD/
├── docker-compose.yml
├── .env
├── run_experiments.py      # Automatiza todos los experimentos
├── analyze.py              # Genera gráficos para el informe
├── response_generator/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── download_dataset.py # Descarga Google Open Buildings
│   └── main.py             # FastAPI + Q1-Q5
├── cache_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # FastAPI + Redis
├── traffic_generator/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # FastAPI + Zipf/Uniforme
├── metrics_storage/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # FastAPI + CSV
└── results/                # Generado automáticamente
    ├── events.csv
    ├── experiments_summary.csv
    ├── summary_table.md
    └── figures/
        ├── dist_comparison.png
        ├── policy_comparison.png
        ├── size_comparison.png
        ├── ttl_comparison.png
        ├── latency_distribution.png
        ├── throughput_timeline.png
        └── hit_rate_by_zone.png
```
