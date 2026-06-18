from __future__ import annotations

import html
import json
import re
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"

SITE_DOMAIN = "okf.impermanente.es"
SITE_URL = f"https://{SITE_DOMAIN}"
SOURCE_BLOG = "https://impermanente.es"
PHOTOS_URL = "https://fotos.impermanente.es"
AUTHOR_NAME = "J.R. Cruciani"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
USER_AGENT = "impermanente-okf/0.1 (+https://okf.impermanente.es/)"
SCRAPE_DELAY_SECONDS = 0.6
POST_RE = re.compile(r"^https://impermanente\.es/(\d{4})/(\d{2})/(\d{2})/([^/]+)\.html$")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class Post:
    url: str
    title: str
    content_html: str
    published: str
    tags: list[str]
    source: str

    @property
    def filename(self) -> str:
        match = POST_RE.match(self.url)
        if not match:
            return slugify(self.title or "nota") + ".md"
        year, month, day, slug = match.groups()
        return f"{year}-{month}-{day}-{slugify(slug)}.md"

    @property
    def year(self) -> str:
        match = POST_RE.match(self.url)
        if match:
            return match.group(1)
        return (self.published or "0000")[:4]

    @property
    def date_prefix(self) -> str:
        match = POST_RE.match(self.url)
        if match:
            return "-".join(match.groups()[:3])
        return (self.published or "0000-00-00")[:10]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))


def sitemap_post_urls() -> list[str]:
    xml = fetch_text(f"{SOURCE_BLOG}/sitemap.xml")
    root = ET.fromstring(xml)
    urls = []
    for loc in root.iter():
        if loc.tag.endswith("loc") and loc.text and POST_RE.match(loc.text.strip()):
            urls.append(loc.text.strip())
    return sorted(set(urls), reverse=True)


def feed_posts() -> dict[str, Post]:
    try:
        feed = fetch_json(f"{SOURCE_BLOG}/feed.json")
    except Exception as exc:  # noqa: BLE001 - build tolerante ante fallo remoto puntual
        print(f"Aviso: no pude leer feed.json: {exc}")
        return {}
    posts = {}
    for item in feed.get("items", []):
        url = item.get("url") or item.get("id") or ""
        if not POST_RE.match(url):
            continue
        posts[url] = Post(
            url=url,
            title=clean_text(item.get("title") or ""),
            content_html=item.get("content_html") or "",
            published=item.get("date_published") or "",
            tags=dedupe(item.get("tags") or []),
            source="feed",
        )
    return posts


class MicroformatParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.in_entry = False
        self.entry_depth = 0
        self.name_depth = 0
        self.category_depth = 0
        self.content_depth = 0
        self.title_parts: list[str] = []
        self.category_parts: list[str] = []
        self.tags: list[str] = []
        self.content_parts: list[str] = []
        self.published = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = set((attrs_dict.get("class") or "").split())
        if "h-entry" in classes and not self.in_entry:
            self.in_entry = True
            self.entry_depth = 1
        elif self.in_entry and tag not in VOID_TAGS:
            self.entry_depth += 1

        if not self.in_entry:
            return
        if ({"p-name", "post-title"} & classes) and not self.title_parts:
            self.name_depth = self.entry_depth
        if ({"p-category", "category"} & classes):
            self.category_depth = self.entry_depth
            self.category_parts = []
        if "dt-published" in classes and not self.published:
            self.published = attrs_dict.get("datetime") or attrs_dict.get("title") or ""
        if "e-content" in classes and not self.content_parts:
            self.content_depth = self.entry_depth

        if self.content_depth:
            self.content_parts.append(render_start_tag(tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.content_depth:
            self.content_parts.append(render_start_tag(tag, attrs, close=True))

    def handle_endtag(self, tag: str) -> None:
        if self.content_depth:
            self.content_parts.append(f"</{tag}>")
        if self.category_depth == self.entry_depth:
            tag_text = clean_text("".join(self.category_parts))
            if tag_text:
                self.tags.append(tag_text)
            self.category_depth = 0
            self.category_parts = []
        if self.name_depth == self.entry_depth:
            self.name_depth = 0
        if self.content_depth == self.entry_depth:
            self.content_depth = 0
        if self.in_entry and tag not in VOID_TAGS:
            self.entry_depth -= 1
            if self.entry_depth <= 0:
                self.in_entry = False

    def handle_data(self, data: str) -> None:
        if self.name_depth:
            self.title_parts.append(data)
        if self.category_depth:
            self.category_parts.append(data)
        if self.content_depth:
            self.content_parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


def render_start_tag(tag: str, attrs: list[tuple[str, str | None]], close: bool = False) -> str:
    bits = [tag]
    for key, value in attrs:
        if value is None:
            bits.append(key)
        else:
            bits.append(f'{key}="{html.escape(value, quote=True)}"')
    return "<" + " ".join(bits) + (" />" if close else ">")


def scrape_post(url: str) -> Post | None:
    parser = MicroformatParser()
    parser.feed(fetch_text(url))
    content = "".join(parser.content_parts).strip()
    if not content:
        return None
    title = clean_text("".join(parser.title_parts))
    return Post(
        url=url,
        title=title,
        content_html=content,
        published=parser.published,
        tags=dedupe(parser.tags),
        source="scrape",
    )


class MarkdownConverter(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article"}
    LIST_TAGS = {"ul", "ol"}
    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[str] = []
        self.list_stack: list[str] = []
        self.skip_depth = 0
        self.just_opened_li = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        attrs_dict = dict(attrs)
        if tag in self.BLOCK_TAGS:
            if self.just_opened_li:
                self.just_opened_li = False
            else:
                self.block()
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "blockquote":
            self.block()
            self.parts.append("> ")
        elif tag in self.LIST_TAGS:
            self.list_stack.append(tag)
            self.block()
        elif tag == "li":
            self.block()
            self.parts.append("* ")
            self.just_opened_li = True
        elif tag in {"h1", "h2", "h3", "h4"}:
            self.block()
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "a":
            self.parts.append("[")
            self.links.append(attrs_dict.get("href") or "")
        elif tag == "img":
            alt = clean_text(attrs_dict.get("alt") or "imagen")
            src = attrs_dict.get("src") or ""
            if src:
                self.parts.append(f"![{alt}]({src})")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in self.BLOCK_TAGS or tag in {"blockquote", "li", "h1", "h2", "h3", "h4"}:
            self.block()
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "a":
            href = self.links.pop() if self.links else ""
            self.parts.append(f"]({href})" if href else "]")
        elif tag in self.LIST_TAGS:
            if self.list_stack:
                self.list_stack.pop()
            self.block()

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            if self.just_opened_li and not data.strip():
                return
            if data.strip():
                self.just_opened_li = False
            self.parts.append(data)

    def block(self) -> None:
        text = "".join(self.parts)
        if not text.endswith("\n\n"):
            self.parts.append("\n\n")

    def markdown(self) -> str:
        text = html.unescape("".join(self.parts))
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_markdown(value: str) -> str:
    parser = MarkdownConverter()
    parser.feed(value or "")
    return parser.markdown()


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return clean_text(" ".join(parser.parts))


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def to_iso8601(value: str) -> str:
    """Normaliza la fecha a ISO 8601.

    micro.blog sirve `dt-published` como 'YYYY-MM-DD HH:MM:SS +0200' (no-ISO),
    mientras que el feed ya viene en ISO. Devuelve el texto original si no encaja.
    """
    text = clean_text(value)
    match = re.match(
        r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)\s*([+-]\d{2}):?(\d{2})?", text
    )
    if not match:
        return text
    date_part, time_part, offset_hours, offset_minutes = match.groups()
    return f"{date_part}T{time_part}{offset_hours}:{offset_minutes or '00'}"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9áéíóúüñ-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "nota"


def dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for raw in values:
        value = clean_text(str(raw)).strip("#")
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def yaml_scalar(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def frontmatter(data: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {yaml_scalar(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def excerpt_from_html(value: str) -> str:
    text = html_to_text(value)
    if not text:
        return "Entrada del blog Impermanente."
    match = re.search(r"(.{40,}?[.!?])\s", text)
    excerpt = match.group(1) if match else text[:200]
    return clean_text(excerpt[:220]).rstrip(" ,;:")


def title_for(post: Post) -> str:
    if post.title:
        return post.title
    text = html_to_text(post.content_html)
    if text:
        return text[:80].rstrip(" ,;:")
    return post.filename.removesuffix(".md")


def description_for(post: Post) -> str:
    """Resumen de una frase. Si el post no tiene texto (solo imágenes),
    recurre al título antes que a un literal genérico."""
    text = html_to_text(post.content_html)
    if text:
        match = re.search(r"(.{40,}?[.!?])\s", text)
        excerpt = match.group(1) if match else text[:200]
        return clean_text(excerpt[:220]).rstrip(" ,;:")
    if post.title:
        return clean_text(post.title)
    return "Entrada con imágenes."


def write_note(post: Post) -> None:
    title = title_for(post)
    markdown = html_to_markdown(post.content_html)
    if not markdown:
        markdown = excerpt_from_html(post.content_html)
    body = (
        frontmatter({
            "type": "Entrada",
            "title": title,
            "description": description_for(post),
            "resource": post.url,
            "tags": post.tags,
            "timestamp": to_iso8601(post.published),
        })
        + markdown
        + f"\n\n# Citations\n\n[1] [Original en impermanente.es]({post.url})\n"
    )
    (OUTPUT_DIR / "notas" / post.filename).write_text(body, encoding="utf-8")


def grouped_by_year(posts: list[Post]) -> dict[str, list[Post]]:
    groups: dict[str, list[Post]] = {}
    for post in posts:
        groups.setdefault(post.year, []).append(post)
    return dict(sorted(groups.items(), reverse=True))


def write_indexes(posts: list[Post]) -> None:
    groups = grouped_by_year(posts)
    root = frontmatter({
        "okf_version": "0.1",
        "title": "Impermanente — bundle OKF",
        "description": "Archivo OKF clonable de las notas públicas de impermanente.es.",
    })
    root += "# Impermanente — OKF\n\n"
    root += "Bundle Open Knowledge Format v0.1 generado desde el blog público.\n\n"
    root += "## Enlaces\n\n"
    root += f"* [Blog original]({SOURCE_BLOG}/) - fuente canónica\n"
    root += f"* [Bundle de fotos]({PHOTOS_URL}/okf/) - OKF visual relacionado\n"
    root += f"* [llms.txt del blog]({SOURCE_BLOG}/llms.txt) - índice para LLMs\n"
    root += "* [Tarball](/okf.tar.gz) - descarga clonable del bundle\n\n"
    root += "## Notas\n\n"
    for year, year_posts in groups.items():
        root += f"### {year}\n\n"
        for post in year_posts:
            root += f"* [{title_for(post)}](/notas/{post.filename}) - {description_for(post)}\n"
        root += "\n"
    (OUTPUT_DIR / "index.md").write_text(root, encoding="utf-8")

    notes = "# Notas\n\n"
    for year, year_posts in groups.items():
        notes += f"## {year}\n\n"
        for post in year_posts:
            notes += f"* [{title_for(post)}]({post.filename}) - {description_for(post)}\n"
        notes += "\n"
    (OUTPUT_DIR / "notas" / "index.md").write_text(notes, encoding="utf-8")


def write_log(posts: list[Post]) -> None:
    today = date.today().isoformat()
    log = f"# Log\n\n* {today} — **Creación** del bundle OKF desde sitemap y feed públicos de impermanente.es.\n"
    for post in posts[:5]:
        log += f"* {post.date_prefix} — **Actualización** incorporada: [{title_for(post)}](/notas/{post.filename}).\n"
    (OUTPUT_DIR / "log.md").write_text(log, encoding="utf-8")


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def write_landing(posts: list[Post], stats: dict[str, int]) -> None:
    latest = posts[0] if posts else None
    latest_link = f'<a href="/notas/{esc(latest.filename)}">{esc(title_for(latest))}</a>' if latest else "sin notas"
    html_doc = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Impermanente — OKF</title>
  <meta name="description" content="Bundle Open Knowledge Format de impermanente.es">
  <style>
    body {{ margin: 0; font-family: Georgia, serif; background: #fbfaf7; color: #171717; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 72px 22px; line-height: 1.65; }}
    h1 {{ font-size: clamp(2.4rem, 8vw, 4.8rem); line-height: 1.05; margin: 0 0 1rem; font-weight: 400; }}
    p {{ font-size: 1.18rem; }}
    a {{ color: #006c67; text-underline-offset: 3px; }}
    ul {{ padding-left: 1.2rem; }}
    .meta {{ font-family: system-ui, sans-serif; font-size: .9rem; color: #666; text-transform: uppercase; letter-spacing: .08em; }}
  </style>
</head>
<body>
  <main>
    <p class="meta">Open Knowledge Format v0.1</p>
    <h1>Impermanente, en Markdown clonable.</h1>
    <p>Este sitio publica un bundle OKF generado desde el contenido público de <a href="{SOURCE_BLOG}/">impermanente.es</a>. GitHub Pages sirve los `.md` crudos en la raíz.</p>
    <ul>
      <li><a href="/index.md">Índice OKF</a></li>
      <li><a href="/okf.tar.gz">Descargar okf.tar.gz</a></li>
      <li><a href="{SOURCE_BLOG}/">Blog original</a></li>
      <li><a href="{PHOTOS_URL}/okf/">Bundle OKF de fotos</a></li>
    </ul>
    <p>{stats['generated']} conceptos generados. Última nota: {latest_link}.</p>
  </main>
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(html_doc, encoding="utf-8")


def make_tarball() -> None:
    tar_path = OUTPUT_DIR / "okf.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for path in sorted(OUTPUT_DIR.rglob("*.md")):
            tar.add(path, arcname=path.relative_to(OUTPUT_DIR))


def validate_output() -> None:
    root_index = (OUTPUT_DIR / "index.md").read_text(encoding="utf-8")
    if not root_index.startswith("---\n") or 'okf_version: "0.1"' not in root_index.split("---", 2)[1]:
        raise SystemExit("Conformance: index.md raíz sin okf_version 0.1")
    for path in OUTPUT_DIR.rglob("*.md"):
        rel = path.relative_to(OUTPUT_DIR).as_posix()
        if path.name in {"index.md", "log.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise SystemExit(f"Conformance: {rel} sin frontmatter")
        fm = text.split("---", 2)[1]
        type_line = next((line for line in fm.splitlines() if line.startswith("type:")), "")
        if not type_line or not type_line.split(":", 1)[1].strip().strip('"'):
            raise SystemExit(f"Conformance: {rel} sin type")
    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file() and bytes((47, 85, 115, 101, 114, 115, 47)) in path.read_bytes():
            raise SystemExit(f"Conformance: ruta absoluta filtrada en {path.relative_to(OUTPUT_DIR)}")


def build() -> dict[str, int]:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    (OUTPUT_DIR / "notas").mkdir(parents=True)
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (OUTPUT_DIR / "CNAME").write_text(SITE_DOMAIN + "\n", encoding="utf-8")

    urls = sitemap_post_urls()
    feed = feed_posts()
    posts: list[Post] = []
    failures: list[tuple[str, str]] = []
    for url in urls:
        post = feed.get(url)
        if not post:
            try:
                post = scrape_post(url)
                time.sleep(SCRAPE_DELAY_SECONDS)
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                failures.append((url, str(exc)))
                continue
            except Exception as exc:  # noqa: BLE001 - tolera páginas viejas raras
                failures.append((url, str(exc)))
                continue
        if not post:
            failures.append((url, "no se encontró e-content"))
            continue
        posts.append(post)

    posts.sort(key=lambda item: item.published or item.url, reverse=True)
    for post in posts:
        write_note(post)
    stats = {
        "sitemap_posts": len(urls),
        "generated": len(posts),
        "feed": sum(1 for post in posts if post.source == "feed"),
        "scraped": sum(1 for post in posts if post.source == "scrape"),
        "failed": len(failures),
    }
    write_indexes(posts)
    write_log(posts)
    write_landing(posts, stats)
    make_tarball()
    validate_output()

    print(
        "OKF generado: "
        f"{stats['generated']}/{stats['sitemap_posts']} posts "
        f"({stats['feed']} feed, {stats['scraped']} scrapeados, {stats['failed']} fallos)."
    )
    for url, error in failures[:10]:
        print(f"Aviso: no capturado {url}: {error}")
    return stats


if __name__ == "__main__":
    build()
