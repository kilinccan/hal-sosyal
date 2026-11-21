"""Günün kuyruğunu Instagram'da yayınlar. Kullanım: IG_TOKEN=... PAGES_URL=https://kullanici.github.io/hal-sosyal/ python -X utf8 paylas.py [--kuru] [--tarih YYYY-MM-DD]"""
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.instagram.com/v27.0"  # https://developers.facebook.com/documentation/instagram-platform/content-publishing
ISTANBUL = timezone(timedelta(hours=3))  # Türkiye'de yaz saati yok
KUYRUK = Path(__file__).resolve().parent / "kuyruk"
BEKLEME_SN, ZAMAN_ASIMI_SN = 10, 300


class Hata(Exception):
    pass


def temizle(metin):
    metin = re.sub(r"(access_token)=[^&\s\"']*", r"\1=***", str(metin))
    metin = re.sub(r"Bearer\s+\S+", "Bearer ***", metin)
    token = os.environ.get("IG_TOKEN")
    return metin.replace(token, "***") if token else metin


def istek(yol, token, veri=None):
    """veri verilirse POST (gövde), yoksa GET; token yalnız Authorization başlığında."""
    gövde = urllib.parse.urlencode(veri).encode() if veri is not None else None
    r = urllib.request.Request(f"{API}/{yol}", data=gövde, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(r, timeout=60) as y:
            return json.load(y)
    except urllib.error.HTTPError as ex:
        raise Hata(temizle(f"{ex.code} {yol}: {ex.read().decode('utf-8', 'replace')}")) from None
    except urllib.error.URLError as ex:
        raise Hata(temizle(f"{yol}: {ex.reason}")) from None


def medya_url(pages, dosya):
    return pages.rstrip("/") + "/" + urllib.parse.quote(dosya.lstrip("/"))


def planla(kayit, pages):
    """[(yol, veri)] istek planı; {c0}, {c1}... önceki container kimliklerinin yer tutucusu."""
    eksik = {"tur", "dosyalar", "aciklama"} - kayit.keys()
    if eksik:
        raise Hata(f"kuyruk kaydında eksik alan: {', '.join(sorted(eksik))}")
    plan = []
    if kayit["tur"] == "carousel":
        if not 2 <= len(kayit["dosyalar"]) <= 10:
            raise Hata("carousel 2-10 görsel olmalı")
        for d in kayit["dosyalar"]:
            plan.append(("me/media", {"image_url": medya_url(pages, d), "is_carousel_item": "true"}))
        kimlikler = ",".join(f"{{c{i}}}" for i in range(len(kayit["dosyalar"])))
        plan.append(("me/media", {"media_type": "CAROUSEL", "children": kimlikler, "caption": kayit["aciklama"]}))
    elif kayit["tur"] == "reel":
        if len(kayit["dosyalar"]) != 1:
            raise Hata("reel için tek dosya gerekir")
        plan.append(("me/media", {"media_type": "REELS", "video_url": medya_url(pages, kayit["dosyalar"][0]),
                                  "caption": kayit["aciklama"]}))
    else:
        raise Hata(f"bilinmeyen tür: {kayit['tur']}")
    return plan


def bekle(kimlik, token):
    bitis = time.monotonic() + ZAMAN_ASIMI_SN
    while True:
        durum = istek(f"{kimlik}?fields=status_code", token).get("status_code")
        if durum == "FINISHED":
            return
        if durum in ("ERROR", "EXPIRED"):
            raise Hata(f"container {kimlik} durumu: {durum}")
        if time.monotonic() > bitis:
            raise Hata(f"container {kimlik} zaman aşımı (son durum: {durum})")
        time.sleep(BEKLEME_SN)


def bugun_paylasildi(token, bugun):
    veri = istek("me/media?fields=timestamp&limit=1", token).get("data", [])
    if not veri:
        return False
    son = datetime.strptime(veri[0]["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(ISTANBUL)
    return son.date() == bugun


def calistir(plan, token):
    kimlikler = []
    for yol, veri in plan:
        veri = {k: v.format(**{f"c{i}": c for i, c in enumerate(kimlikler)}) if k == "children" else v
                for k, v in veri.items()}
        kimlik = istek(yol, token, veri)["id"]
        bekle(kimlik, token)
        kimlikler.append(kimlik)
    return istek("me/media_publish", token, {"creation_id": kimlikler[-1]})["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="ağ isteği yapmadan planı yazdır")
    ap.add_argument("--tarih", help="YYYY-MM-DD (test)")
    ap.add_argument("--kontrol", action="store_true", help="yalnız token'ı dener, paylaşmaz")
    a = ap.parse_args()
    if a.kontrol:
        hesap = istek("me?fields=username,account_type", os.environ.get("IG_TOKEN", ""))
        print("bağlantı tamam:", hesap.get("username"), hesap.get("account_type"))
        return 0
    bugun = datetime.strptime(a.tarih, "%Y-%m-%d").date() if a.tarih else datetime.now(ISTANBUL).date()
    dosya = KUYRUK / f"{bugun.isoformat()}.json"
    if not dosya.exists():
        print("::warning::kuyruk boş")
        return 0
    kayit = json.loads(dosya.read_text(encoding="utf-8"))
    pages = os.environ.get("PAGES_URL")
    if not pages:
        raise Hata("PAGES_URL tanımlı değil")
    plan = planla(kayit, pages)
    if a.kuru:
        for yol, veri in plan:
            print("POST", f"{API}/{yol}", json.dumps(veri, ensure_ascii=False))
        print("POST", f"{API}/me/media_publish", '{"creation_id": "<son container>"}')
        return 0
    token = os.environ.get("IG_TOKEN")
    if not token:
        raise Hata("IG_TOKEN tanımlı değil")
    if bugun_paylasildi(token, bugun):
        print("bugün zaten paylaşılmış")
        return 0
    print("yayınlandı:", calistir(plan, token))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Hata as ex:
        print("HATA:", temizle(ex), file=sys.stderr)
        sys.exit(1)
