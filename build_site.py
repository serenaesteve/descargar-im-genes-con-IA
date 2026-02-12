#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

UPDATED_XML_FILE = "producto.updated.xml"   # usa el xml ya actualizado con tus imágenes
SITE_DIR = Path("site")

def text(el, path):
    node = el.find(path)
    return (node.text or "").strip() if node is not None and node.text else ""

def main():
    if not Path(UPDATED_XML_FILE).exists():
        raise FileNotFoundError("Primero ejecuta generate_assets.py para crear producto.updated.xml")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "images").mkdir(parents=True, exist_ok=True)

    # Copia imágenes generadas dentro de la web
    gen_dir = Path("generated_images")
    if gen_dir.exists():
        for f in gen_dir.glob("*.png"):
            shutil.copy2(f, SITE_DIR / "images" / f.name)

    tree = ET.parse(UPDATED_XML_FILE)
    root = tree.getroot()

    title = text(root, "./meta/title")
    category = text(root, "./meta/category")
    value = text(root, "./hero/valueProposition")
    subtitle = text(root, "./hero/subtitle")
    hero_img = root.find("./hero/media/image").attrib.get("src", "")

    # Ajusta rutas: generated_images/... -> images/...
    hero_img = hero_img.replace("generated_images/", "images/")

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="assets/style.css" />
</head>
<body>
  <header class="nav">
    <div class="brand">{title}</div>
    <div class="pill">{category}</div>
    <button id="themeBtn" class="btn">Modo oscuro</button>
  </header>

  <main class="container">
    <section class="hero">
      <div class="heroText">
        <h1>{value}</h1>
        <p>{subtitle}</p>
        <div class="actions">
          <a class="btn primary" href="#cta">Adoptar</a>
          <a class="btn" href="#cta">Donar</a>
        </div>
      </div>
      <div class="heroMedia">
        <img src="{hero_img}" alt="hero" />
      </div>
    </section>

    {render_section(root, "problem", "problem")}
    {render_section(root, "solution", "solution")}
    {render_section(root, "keyFeatures", "features")}
    {render_section(root, "benefits", "benefits")}
    {render_section(root, "finalCTA", "cta", anchor="cta")}

  </main>

  <script src="assets/app.js"></script>
</body>
</html>
"""

    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

    # assets
    (SITE_DIR / "assets" / "style.css").write_text(DEFAULT_CSS, encoding="utf-8")
    (SITE_DIR / "assets" / "app.js").write_text(DEFAULT_JS, encoding="utf-8")

    print("Web generada en: site/index.html")

def render_section(root, tag, section_name, anchor=None):
    sec = root.find(f"./{tag}")
    if sec is None:
        return ""

    title = (sec.findtext("title") or "").strip()
    img_el = sec.find("./media/image")
    img_src = (img_el.attrib.get("src") if img_el is not None else "") or ""
    img_src = img_src.replace("generated_images/", "images/")

    body = ""

    if tag == "problem":
        items = [ (x.text or "").strip() for x in sec.findall("./items/item") ]
        body = "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    if tag == "solution":
        overview = (sec.findtext("overview") or "").strip()
        changes = [ (x.text or "").strip() for x in sec.findall("./whatChanges/change") ]
        body = f"<p>{overview}</p>" + "<ul>" + "".join(f"<li>{c}</li>" for c in changes) + "</ul>"

    if tag == "keyFeatures":
        feats = []
        for f in sec.findall("./feature"):
            n = (f.findtext("name") or "").strip()
            b = (f.findtext("benefit") or "").strip()
            feats.append((n, b))
        body = "<div class='grid'>" + "".join(
            f"<div class='card'><h3>{n}</h3><p>{b}</p></div>" for n,b in feats
        ) + "</div>"

    if tag == "benefits":
        items = [ (x.text or "").strip() for x in sec.findall("./items/item") ]
        body = "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    if tag == "finalCTA":
        desc = (sec.findtext("description") or "").strip()
        body = f"<p>{desc}</p><div class='actions'><a class='btn primary' href='#'>Adoptar</a><a class='btn' href='#'>Donar</a></div>"

    a = f" id='{anchor}'" if anchor else ""
    return f"""
<section class="section"{a}>
  <div class="sectionHead">
    <h2>{title}</h2>
  </div>
  <div class="sectionBody">
    <div class="sectionMedia"><img src="{img_src}" alt="{section_name}" /></div>
    <div class="sectionContent">{body}</div>
  </div>
</section>
"""

DEFAULT_CSS = """
:root{--bg:#0b0c10;--card:#11131a;--text:#e8eaf0;--muted:#b6bccb;--primary:#7ee081;--border:#242838;}
body.light{--bg:#f6f7fb;--card:#ffffff;--text:#121318;--muted:#4b5563;--primary:#1f7a3a;--border:#e5e7eb;}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,Arial;background:var(--bg);color:var(--text);}
.container{max-width:1100px;margin:0 auto;padding:24px;}
.nav{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);}
.brand{font-weight:700} .pill{padding:6px 10px;border:1px solid var(--border);border-radius:999px;color:var(--muted)}
.btn{border:1px solid var(--border);background:transparent;color:var(--text);padding:10px 14px;border-radius:10px;cursor:pointer;text-decoration:none;display:inline-block}
.btn.primary{background:var(--primary);border-color:var(--primary);color:#0b0c10;font-weight:700}
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;align-items:center;margin-top:18px}
.heroMedia img{width:100%;border-radius:18px;border:1px solid var(--border)}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.section{margin:34px 0;padding:18px;border:1px solid var(--border);border-radius:18px;background:var(--card)}
.sectionBody{display:grid;grid-template-columns:.9fr 1.1fr;gap:16px;align-items:start}
.sectionMedia img{width:100%;border-radius:14px;border:1px solid var(--border)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.card{padding:14px;border:1px solid var(--border);border-radius:14px;background:transparent}
h1{font-size:38px;line-height:1.05;margin:0} h2{margin:0 0 12px} h3{margin:0 0 6px}
p{color:var(--muted);margin:10px 0}
ul{margin:0;padding-left:18px;color:var(--muted)} li{margin:8px 0}
@media (max-width:900px){.hero,.sectionBody{grid-template-columns:1fr}.grid{grid-template-columns:1fr} h1{font-size:30px}}
"""

DEFAULT_JS = """
const btn = document.getElementById('themeBtn');
const key = 'theme_light';
function apply() {
  const isLight = localStorage.getItem(key) === '1';
  document.body.classList.toggle('light', isLight);
  btn.textContent = isLight ? 'Modo oscuro' : 'Modo claro';
}
btn?.addEventListener('click', () => {
  const isLight = localStorage.getItem(key) === '1';
  localStorage.setItem(key, isLight ? '0' : '1');
  apply();
});
apply();
"""

if __name__ == "__main__":
    main()

