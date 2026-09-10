#!/usr/bin/env python3
"""Baixa uma pintura de domínio público ou CC por santo, no Wikimedia Commons."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images" / "saints"
CREDITS = ROOT / "images" / "credits.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "a-vida-dos-santos/0.1 (personal non-commercial edition; pfelrodrigues)"

OK_LICENSES = (
    "public domain",
    "pd-",
    "cc0",
    "cc by",
    "cc-by",
    "cc by-sa",
    "cc-by-sa",
)

SEARCH = {
    "sao-sebastiao": "Saint Sebastian painting",
    "santa-ines": "Saint Agnes of Rome painting",
    "sao-vicente-pallotti": "Vincent Pallotti portrait",
    "santos-timoteo-e-tito": "Saints Timothy and Titus",
    "sao-joao-bosco": "John Bosco portrait",
    "sao-bras": "Saint Blaise painting",
    "nossa-senhora-de-lourdes": "Our Lady of Lourdes painting",
    "santa-eulalia": "Saint Eulalia of Barcelona painting",
    "santos-cirilo-e-metodio": "Saints Cyril and Methodius painting",
    "sao-policarpo": "Saint Polycarp painting",
    "sao-casimiro": "Saint Casimir painting",
    "sao-joao-de-deus": "Saint John of God painting",
    "sao-jose-padroeiro-da-igreja": "Saint Joseph painting",
    "sao-turibio-de-mongrovejo": "Turibius of Mogrovejo",
    "sao-joao-batista-de-la-salle": "Jean-Baptiste de La Salle portrait",
    "sao-jorge": "Saint George and the Dragon painting",
    "sao-marcos": "Saint Mark the Evangelist painting",
    "santa-catarina-de-sena": "Catherine of Siena painting",
    "sao-atanasio": "Athanasius of Alexandria painting",
    "sao-bernardino-de-sena": "Bernardino of Siena painting",
    "santa-rita-de-cassia": "Rita of Cascia painting",
    "sao-bonifacio": "Saint Boniface painting",
    "santo-antonio": "Anthony of Padua painting",
    "sao-luis-gonzaga": "Aloysius Gonzaga painting",
    "sao-joao-fisher-e-santo-tomas-more": "Thomas More Holbein",
    "natividade-de-joao-batista": "Birth of John the Baptist painting",
    "sao-pedro-e-sao-paulo": "Saints Peter and Paul painting",
    "santa-isabel-de-portugal": "Elizabeth of Portugal painting",
    "santa-maria-goretti": "Maria Goretti portrait",
    "sao-camilo-de-lelis": "Camillus de Lellis painting",
    "sant-ana-e-sao-joaquim": "Saint Anne and Saint Joachim painting",
    "santo-inacio-de-loiola": "Ignatius of Loyola painting",
    "sao-joao-maria-vianney": "Jean-Marie Vianney portrait",
    "sao-domingos": "Saint Dominic painting",
    "santa-clara": "Clare of Assisi painting",
    "sao-maximiliano-kolbe": "Maximilian Kolbe portrait",
    "sao-bartolomeu": "Saint Bartholomew apostle painting",
    "sao-luis-rei-de-franca": "Louis IX of France painting",
    "santa-monica": "Saint Monica painting",
    "sao-gregorio-magno": "Pope Gregory I painting",
    "sao-pedro-claver": "Peter Claver portrait",
    "sao-francisco-das-chagas": "Saint Francis receiving the stigmata painting",
    "sao-cosme-e-sao-damiao": "Saints Cosmas and Damian painting",
    "sao-vicente-de-paulo": "Vincent de Paul painting",
    "sao-jeronimo": "Saint Jerome painting",
    "santa-teresinha-do-menino-jesus": "Therese of Lisieux portrait",
    "sao-francisco-de-assis": "Francis of Assisi painting",
    "nossa-senhora-aparecida": "Our Lady of Aparecida",
    "santa-teresa-de-avila": "Teresa of Avila painting",
    "sao-geraldo-magela": "Gerard Majella portrait",
    "santa-hedviges": "Hedwig of Silesia painting",
    "sao-lucas": "Saint Luke the Evangelist painting",
    "santa-isabel-da-hungria": "Elizabeth of Hungary painting",
    "santa-cecilia": "Saint Cecilia painting",
    "santo-andre": "Saint Andrew apostle painting",
    "santo-ambrosio": "Saint Ambrose painting",
    "imaculada-conceicao": "Immaculate Conception Murillo",
    "santa-luzia": "Saint Lucy painting",
    "sao-joao-da-cruz": "John of the Cross painting",
    "santo-estevao": "Saint Stephen martyr painting",
    "sao-joao-evangelista": "Saint John the Evangelist painting",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def license_ok(name: str) -> bool:
    n = name.lower()
    if "fair use" in n or "non-free" in n:
        return False
    return any(token in n for token in OK_LICENSES)


def search(query: str) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": "6",
        "gsrlimit": "12",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": "1200",
    }
    data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
    pages = data.get("query", {}).get("pages", {})
    hits = []
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName", {}) or {}).get("value", "")
        if not license_ok(lic):
            continue
        mime = info.get("mime") or ""
        if not mime.startswith("image/"):
            continue
        hits.append(
            {
                "title": page.get("title"),
                "thumb": info.get("thumburl") or info.get("url"),
                "url": info.get("descriptionurl"),
                "license": lic,
                "artist": (meta.get("Artist", {}) or {}).get("value", ""),
                "credit": (meta.get("Credit", {}) or {}).get("value", ""),
            }
        )
    return hits


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    if CREDITS.exists():
        credits = json.loads(CREDITS.read_text(encoding="utf-8"))
    missing = []
    for piece_id, query in SEARCH.items():
        dest = OUT / f"{piece_id}.jpg"
        if dest.exists() and dest.stat().st_size > 2000:
            print(f"skip {piece_id}")
            continue
        print(f"search {piece_id}: {query}")
        try:
            hits = search(query)
        except Exception as exc:
            print(f"  fail search: {exc}")
            missing.append(piece_id)
            time.sleep(0.4)
            continue
        if not hits:
            print("  none")
            missing.append(piece_id)
            time.sleep(0.4)
            continue
        hit = hits[0]
        try:
            blob = get(hit["thumb"])
            dest.write_bytes(blob)
        except Exception as exc:
            print(f"  fail download: {exc}")
            missing.append(piece_id)
            time.sleep(0.4)
            continue
        credits[piece_id] = {
            "query": query,
            "title": hit["title"],
            "page": hit["url"],
            "license": hit["license"],
            "artist": strip_html(hit["artist"]),
            "credit": strip_html(hit["credit"]),
            "file": f"images/saints/{piece_id}.jpg",
        }
        print(f"  ok {hit['license']} {hit['title']}")
        time.sleep(0.4)
    CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"got {len(credits)} missing {len(missing)}")
    if missing:
        print("missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
