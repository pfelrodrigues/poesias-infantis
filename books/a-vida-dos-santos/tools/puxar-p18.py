#!/usr/bin/env python3
"""Puxa a imagem principal (P18) de cada santo no Wikidata, se a licença for livre."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images" / "saints"
CREDITS = ROOT / "images" / "credits.json"
WD = "https://www.wikidata.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = "a-vida-dos-santos/0.1 (personal non-commercial edition; pfelrodrigues)"

OK = ("public domain", "pd-", "cc0", "cc by", "cc-by", "cc by-sa", "cc-by-sa")

# Consulta Wikidata, não busca solta no Commons.
QIDS = {
    "sao-sebastiao": "Q331357",
    "santa-ines": "Q166325",
    "sao-vicente-pallotti": "Q353829",
    "santos-timoteo-e-tito": "Q243102",  # Timothy; pair image rare
    "sao-joao-bosco": "Q184434",
    "sao-bras": "Q155375",
    "nossa-senhora-de-lourdes": "Q49478",
    "santa-eulalia": "Q236388",
    "santos-cirilo-e-metodio": "Q179826",
    "sao-policarpo": "Q272078",
    "sao-casimiro": "Q312685",
    "sao-joao-de-deus": "Q379954",
    "sao-jose-padroeiro-da-igreja": "Q128267",
    "sao-turibio-de-mongrovejo": "Q467971",
    "sao-joao-batista-de-la-salle": "Q269324",
    "sao-jorge": "Q48438",
    "sao-marcos": "Q31966",
    "santa-catarina-de-sena": "Q229639",
    "sao-atanasio": "Q44024",
    "sao-bernardino-de-sena": "Q312656",
    "santa-rita-de-cassia": "Q232818",
    "sao-bonifacio": "Q46765",
    "santo-antonio": "Q43933",
    "sao-luis-gonzaga": "Q311887",
    "sao-joao-fisher-e-santo-tomas-more": "Q60059",  # More; Fisher Q315496
    "natividade-de-joao-batista": "Q40662",
    "sao-pedro-e-sao-paulo": "Q33923",  # Peter; Paul Q9200
    "santa-isabel-de-portugal": "Q236932",
    "santa-maria-goretti": "Q193479",
    "sao-camilo-de-lelis": "Q311815",
    "sant-ana-e-sao-joaquim": "Q164294",  # Anne
    "santo-inacio-de-loiola": "Q44281",
    "sao-joao-maria-vianney": "Q184866",
    "sao-domingos": "Q44091",
    "santa-clara": "Q157094",
    "sao-maximiliano-kolbe": "Q159508",
    "sao-bartolomeu": "Q43999",
    "sao-luis-rei-de-franca": "Q346",
    "santa-monica": "Q234934",
    "sao-gregorio-magno": "Q42827",
    "sao-pedro-claver": "Q315497",
    "sao-francisco-das-chagas": "Q676555",
    "sao-cosme-e-sao-damiao": "Q330863",
    "sao-vicente-de-paulo": "Q184575",
    "sao-jeronimo": "Q44248",
    "santa-teresinha-do-menino-jesus": "Q45274",
    "sao-francisco-de-assis": "Q676555",
    "nossa-senhora-aparecida": "Q477074",
    "santa-teresa-de-avila": "Q174880",
    "sao-geraldo-magela": "Q561639",
    "santa-hedviges": "Q157002",
    "sao-lucas": "Q128538",
    "santa-isabel-da-hungria": "Q159316",
    "santa-cecilia": "Q231381",
    "santo-andre": "Q43399",
    "santo-ambrosio": "Q43689",
    "imaculada-conceicao": "Q185176",
    "santa-luzia": "Q161869",
    "sao-joao-da-cruz": "Q188900",
    "santo-estevao": "Q161775",
    "sao-joao-evangelista": "Q44015",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read()


def api(base: str, **params) -> dict:
    params["format"] = "json"
    return json.loads(get(base + "?" + urllib.parse.urlencode(params)))


def license_ok(name: str) -> bool:
    n = (name or "").lower()
    if "fair use" in n or "non-free" in n:
        return False
    return any(t in n for t in OK)


def p18(qid: str) -> str | None:
    data = api(
        WD,
        action="wbgetentities",
        ids=qid,
        props="claims",
        languages="en",
    )
    claims = data["entities"][qid].get("claims", {})
    images = claims.get("P18") or []
    if not images:
        return None
    return images[0]["mainsnak"]["datavalue"]["value"]


def commons_info(filename: str) -> dict | None:
    data = api(
        COMMONS,
        action="query",
        titles="File:" + filename,
        prop="imageinfo",
        iiprop="url|extmetadata|mime",
        iiurlwidth="1200",
    )
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            return None
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not license_ok(lic):
            return None
        return {
            "title": page.get("title"),
            "thumb": info.get("thumburl") or info.get("url"),
            "url": info.get("descriptionurl"),
            "license": lic,
            "artist": (meta.get("Artist") or {}).get("value", ""),
        }
    return None


def strip(value: str) -> str:
    import re

    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    missing = []
    for piece_id, qid in QIDS.items():
        dest = OUT / f"{piece_id}.jpg"
        print(f"{piece_id} {qid}")
        try:
            filename = p18(qid)
            if not filename:
                print("  no P18")
                missing.append(piece_id)
                time.sleep(1.0)
                continue
            info = commons_info(filename)
            if not info:
                print(f"  no free license: {filename}")
                missing.append(piece_id)
                time.sleep(1.0)
                continue
            dest.write_bytes(get(info["thumb"]))
        except Exception as exc:
            print(f"  fail: {exc}")
            missing.append(piece_id)
            time.sleep(1.2)
            continue
        credits[piece_id] = {
            "wikidata": f"https://www.wikidata.org/wiki/{qid}",
            "title": info["title"],
            "page": info["url"],
            "license": info["license"],
            "artist": strip(info["artist"]),
            "file": f"images/saints/{piece_id}.jpg",
        }
        print(f"  ok {info['license']} {info['title']}")
        time.sleep(1.0)
    CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"got {len(credits)} missing {len(missing)}")
    if missing:
        print("missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
