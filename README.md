# impermanente-okf

Generador estático del bundle **Open Knowledge Format (OKF) v0.1** de [`impermanente.es`](https://impermanente.es/). El blog vive en micro.blog; este repo crea una copia clonable en Markdown con frontmatter YAML y la sirve en `https://okf.impermanente.es/`.

## Build local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/build_site.py
```

La salida va a `output/` e incluye `index.md`, `log.md`, `notas/*.md`, `okf.tar.gz`, `.nojekyll`, `CNAME` e `index.html`.

## Fuente

- `https://impermanente.es/sitemap.xml` enumera el archivo completo.
- `https://impermanente.es/feed.json` enriquece los posts recientes.
- Los posts antiguos se leen desde HTML público con microformats2 (`h-entry`, `p-name`, `e-content`, `dt-published`, `p-category`).

## Deploy

GitHub Actions construye `output/` y lo publica en `gh-pages` con `peaceiris/actions-gh-pages`. Tras crear el repo remoto y hacer push, configurar GitHub Pages para `gh-pages` y añadir el DNS `CNAME okf.impermanente.es -> jrcruciani.github.io`.

## Licencia

Contenido: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — J.R. Cruciani.
