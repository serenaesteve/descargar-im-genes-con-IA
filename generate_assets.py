#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline


# =========================
# CONFIG
# =========================
XML_FILE = "producto.xml"
UPDATED_XML_FILE = "producto.updated.xml"
OUTPUT_DIR = "generated_images"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3"
OLLAMA_TIMEOUT = 300

MODEL_ID = "runwayml/stable-diffusion-v1-5"

STEPS = 30
GUIDANCE = 7.5
SEED_BASE = 12345

# Resoluciones optimizadas para 6GB (RTX 4050)
SECTION_SIZE = {
    "hero": (768, 432),
    "problem": (768, 432),
    "solution": (768, 432),
    "features": (640, 640),
    "benefits": (768, 432),
    "cta": (768, 432),
    "misc": (768, 432),
}


# =========================
# UTILIDADES
# =========================
def slugify(s: str, maxlen: int = 80) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s)
    s = s.strip("-") or "image"
    return s[:maxlen]


def safe_filename(section: str, alt: str) -> str:
    return f"{slugify(section)}-{slugify(alt)}.png"


def build_context(root: ET.Element) -> dict:
    def get_text(path: str) -> str:
        el = root.find(path)
        return (el.text or "").strip() if el is not None and el.text else ""

    return {
        "title": get_text("./meta/title"),
        "category": get_text("./meta/category"),
        "slug": get_text("./meta/slug"),
        "valueProposition": get_text("./hero/valueProposition"),
        "subtitle": get_text("./hero/subtitle"),
        "style": {
            "look": "clean, warm, modern animal shelter landing, cinematic lighting, ultra detailed",
            "avoid": "text, letters, logos, watermark",
        }
    }


def collect_images(root: ET.Element):
    section_paths = {
        "hero": "./hero",
        "problem": "./problem",
        "solution": "./solution",
        "features": "./keyFeatures",
        "benefits": "./benefits",
        "cta": "./finalCTA",
    }

    items = []

    for section, path in section_paths.items():
        el = root.find(path)
        if el is None:
            continue
        for img in el.findall(".//image"):
            items.append({
                "element": img,
                "section": section,
                "src": (img.attrib.get("src") or "").strip(),
                "alt": (img.attrib.get("alt") or "").strip(),
            })

    if not items:
        for img in root.findall(".//image"):
            items.append({
                "element": img,
                "section": "misc",
                "src": (img.attrib.get("src") or "").strip(),
                "alt": (img.attrib.get("alt") or "").strip(),
            })

    return items


# =========================
# OLLAMA JSON ROBUSTO
# =========================
def ollama_generate_json(system: str, user: str) -> dict:

    def extract_json(t: str) -> str:
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return t[start:end+1]
        return t

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": user,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2},
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    r.raise_for_status()
    raw = (r.json().get("response") or "").strip()
    js = extract_json(raw)

    try:
        return json.loads(js)
    except json.JSONDecodeError:
        # Reintento forzando JSON estricto
        payload["options"]["temperature"] = 0.0
        payload["prompt"] = user + "\n\nRESPONDE SOLO CON JSON VÁLIDO. SIN TEXTO EXTRA."
        r2 = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        r2.raise_for_status()
        raw2 = (r2.json().get("response") or "").strip()
        js2 = extract_json(raw2)
        return json.loads(js2)


def ask_prompts(context: dict, images):

    system = (
        "Eres un generador de prompts para Stable Diffusion. "
        "Debes devolver SOLO JSON válido. "
        "Sin texto adicional. Sin markdown."
    )

    req = [{"id": i+1, "section": x["section"], "alt": x["alt"]} for i, x in enumerate(images)]

    user = (
        f"Contexto:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "Devuelve JSON con este formato:\n"
        '{"images":[{"id":1,"prompt":"...","negative_prompt":"..."}]}\n\n'
        f"Lista:\n{json.dumps(req, ensure_ascii=False, indent=2)}\n\n"
        "Prompt en INGLÉS. Negative prompt fuerte contra texto, logos y watermarks.\n"
        "Devuelve SOLO JSON."
    )

    data = ollama_generate_json(system, user)
    by_id = {d["id"]: d for d in data.get("images", []) if "id" in d}

    results = []

    for i in range(1, len(images)+1):
        d = by_id.get(i, {})
        prompt = d.get("prompt") or "warm animal shelter, cinematic lighting, ultra detailed photo"
        neg = d.get("negative_prompt") or "text, letters, watermark, logo, brand, blurry"
        results.append({"prompt": prompt, "negative_prompt": neg})

    return results


# =========================
# STABLE DIFFUSION
# =========================
def load_pipe():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        safety_checker=None,
    ).to(device)

    if device == "cuda":
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
        pipe.enable_attention_slicing()
        try:
            pipe.enable_vae_slicing()
        except Exception:
            pass

    return pipe


# =========================
# MAIN
# =========================
def main():
    tree = ET.parse(XML_FILE)
    root = tree.getroot()

    context = build_context(root)
    images = collect_images(root)

    print(f"Encontradas {len(images)} imágenes en XML.")
    print("Pidiendo prompts a Ollama...")

    prompts = ask_prompts(context, images)

    print("Cargando Stable Diffusion...")
    pipe = load_pipe()

    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, (img_info, pr) in enumerate(zip(images, prompts), start=1):

        section = img_info["section"]
        alt = img_info["alt"] or f"image-{idx}"
        filename = safe_filename(section, alt)
        out_path = out_dir / filename

        if not out_path.exists():
            w, h = SECTION_SIZE.get(section, SECTION_SIZE["misc"])
            seed = SEED_BASE + idx
            gen_device = "cuda" if pipe.device.type == "cuda" else "cpu"
            g = torch.Generator(gen_device).manual_seed(seed)

            print(f"[{idx}/{len(images)}] Generando {filename} ({w}x{h})")

            result = pipe(
                prompt=pr["prompt"],
                negative_prompt=pr["negative_prompt"],
                num_inference_steps=STEPS,
                guidance_scale=GUIDANCE,
                width=w,
                height=h,
                generator=g,
            )

            result.images[0].save(out_path)

        img_info["element"].set("src", str(Path(OUTPUT_DIR) / filename))

    tree.write(UPDATED_XML_FILE, encoding="utf-8", xml_declaration=True)

    print(f"\n✔ XML actualizado guardado en {UPDATED_XML_FILE}")
    print("✔ Imágenes generadas en carpeta generated_images/")


if __name__ == "__main__":
    main()

