# AGENTS.md — Runbook operativo

## Contexto

`impermanente-okf` genera un bundle OKF v0.1 de `https://impermanente.es/` y lo despliega como sitio estático en `https://okf.impermanente.es/`.

## Regenerar

```bash
cd ~/Proyectos/impermanente-okf
source .venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt
python3 scripts/build_site.py
```

El build consulta `sitemap.xml` y scrapea el HTML público de todas las entradas para conservar el contenido y los textos `alt` actuales. `feed.json` solo completa metadatos ausentes. Si falla cualquier entrada, aborta el deploy y conserva la versión anterior.

## Deploy

Push a `main` dispara `.github/workflows/build.yml`; el cron corre cada 12h. No se commitea `output/` ni `.venv/`.

## Convenciones

- Código en inglés; docs, UI y errores en español.
- Sin rutas absolutas ni secretos en repo.
- Dependencias mínimas: hoy solo stdlib.
