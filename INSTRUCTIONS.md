# 🚀 Guía de Ejecución y Pruebas - Tarea 1 SD

Esta guía contiene los pasos necesarios para desplegar y probar la plataforma de análisis de edificios.

## 📋 Requisitos Previos

1.  **Docker Desktop**: Asegúrate de que esté instalado y **en ejecución**.
2.  **Python 3.10+**: Instalado localmente.
3.  **Librerías de Python**: Instala las dependencias necesarias con el siguiente comando:
    ```powershell
    pip install httpx pandas matplotlib pyarrow s2sphere
    ```

---

## 🛠️ Paso a Paso para la Ejecución

### 1. Clonar el Repositorio
```powershell
git clone https://github.com/Jalann18/Tarea_1_SD
cd Tarea_1_SD
```

### 2. Levantar la Infraestructura
Inicia los contenedores de Docker (Redis, Generador de Tráfico, etc.):
```powershell
docker compose up -d
```

### 3. Cargar el Dataset Real
Este repositorio ya incluye el dataset filtrado para Santiago en la carpeta `data/`. Debes cargarlo manualmente al contenedor del generador de respuestas:
```powershell
docker cp data/santiago_buildings.parquet response_generator:/data/santiago_buildings.parquet
docker compose restart response_generator
```

### 4. Ejecutar la Batería de Experimentos
Este script automatiza 11 pruebas distintas (cambiando políticas de caché, tamaños y distribuciones):
```powershell
python run_experiments.py
```
*El progreso se mostrará en la consola. Tardará aproximadamente 5-8 minutos.*

### 5. Generar Reporte y Gráficos
Una vez que los experimentos terminen, extrae los eventos detallados y genera el análisis visual:
```powershell
# Extraer eventos del contenedor de métricas
docker cp metrics_storage:/metrics/events.csv results/events.csv

# Generar gráficos y tabla resumen
python analyze.py
```

---

## 📁 Resultados
Tras completar los pasos, encontrarás:
*   **Gráficos**: En `results/figures/` (Comparativas de hit rate, latencia, etc.).
*   **Tabla Resumen**: En `results/summary_table.md` (Lista de todos los resultados en formato Markdown).

---

## 🔍 Verificación Manual
Si deseas probar un endpoint específico manualmente:
*   **Cache Stats**: `http://localhost:8002/stats`
*   **Métricas**: `http://localhost:8003/docs`
*   **Traffic Generator Docs**: `http://localhost:8004/docs`
