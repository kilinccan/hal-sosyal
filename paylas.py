"""O saatin kuyruğunu Instagram'da yayınlar. Kullanım: IG_TOKEN=... PAGES_URL=https://kullanici.github.io/hal-sosyal/ python -X utf8 paylas.py [--kuru] [--tarih YYYY-MM-DD] [--saat HH]
Kuyruk: kuyruk/YYYY-MM-DD-HHMM.json (HH ∈ SAATLER); eski YYYY-MM-DD.json 21:00 sayılır.
Kayıt: {tur, dosyalar, aciklama}; reel için isteğe bağlı "trial": true (Trial Reel, MANUAL mezuniyet)."""
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.facebook.com/v27.0"  # Unified login, system-user token: https://developers.facebook.com/documentation/instagram-platform/content-publishing
HESAP = os.environ.get("IG_USER_ID", "")
ISTANBUL = timezone(timedelta(hours=3))  # Türkiye'de yaz saati yok
KUYRUK = Path(os.environ.get("VERI_KOKU") or Path(__file__).resolve().parent) / "kuyruk"  # veri yayin dalında, kod main'de
BEKLEME_SN, ZAMAN_ASIMI_SN = 10, 300
SAATLER = (9, 11, 13, 18, 21)  # paylas.yml cron'u ile aynı (TR saati)


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
    gerekli = {"tur", "dosyalar"} if kayit.get("tur") == "hikaye" else {"tur", "dosyalar", "aciklama"}
    eksik = gerekli - kayit.keys()
    if eksik:
        raise Hata(f"kuyruk kaydında eksik alan: {', '.join(sorted(eksik))}")
    trial = kayit.get("trial")
    if trial is not None and not isinstance(trial, bool):
        raise Hata("trial true/false olmalı")
    if trial and kayit["tur"] != "reel":
        raise Hata("trial yalnız reel için")
    plan = []
    if kayit["tur"] == "hikaye":  # 9:16; açıklama alanı API'de yok
        if len(kayit["dosyalar"]) != 1:
            raise Hata("hikaye için tek dosya gerekir")
        d = kayit["dosyalar"][0]
        alan = "video_url" if d.lower().endswith(".mp4") else "image_url"
        plan.append((f"{HESAP}/media", {"media_type": "STORIES", alan: medya_url(pages, d)}))
    elif kayit["tur"] == "carousel":
        if not 2 <= len(kayit["dosyalar"]) <= 10:
            raise Hata("carousel 2-10 görsel olmalı")
        for d in kayit["dosyalar"]:
            plan.append((f"{HESAP}/media", {"image_url": medya_url(pages, d), "is_carousel_item": "true"}))
        kimlikler = ",".join(f"{{c{i}}}" for i in range(len(kayit["dosyalar"])))
        plan.append((f"{HESAP}/media", {"media_type": "CAROUSEL", "children": kimlikler, "caption": kayit["aciklama"]}))
    elif kayit["tur"] == "gorsel":
        if len(kayit["dosyalar"]) != 1:
            raise Hata("görsel için tek dosya gerekir")
        plan.append((f"{HESAP}/media", {"image_url": medya_url(pages, kayit["dosyalar"][0]), "caption": kayit["aciklama"]}))
    elif kayit["tur"] == "reel":
        if len(kayit["dosyalar"]) != 1:
            raise Hata("reel için tek dosya gerekir")
        # kapak: varsayılan ilk kare siyah (videolar karartmayla açılır); 2. saniyedeki kare kullanılır
        veri = {"media_type": "REELS", "video_url": medya_url(pages, kayit["dosyalar"][0]),
                "caption": kayit["aciklama"], "thumb_offset": "2000"}
        if trial:
            veri["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"}  # iyi giderse takipçilere kendiliğinden açılır, separators=(",", ":"))
        plan.append((f"{HESAP}/media", veri))
    else:
        raise Hata(f"bilinmeyen tür: {kayit['tur']}")
    return plan


def dosyalari_dogrula(dosyalar):
    """Yol veri kökünde var olmalı; ters eğik çizgi Windows'ta bulunur ama Pages'te 404 verir."""
    kok = KUYRUK.parent.resolve()
    bozuk = [d for d in dosyalar
             if "\\" in d or not (kok / d).resolve().is_relative_to(kok) or not (kok / d).is_file()]
    if bozuk:
        raise Hata(f"medya yolu bozuk ya da dosya yok: {', '.join(bozuk)}")


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


def dilim(simdi):
    """simdi'ye göre bu çalışmanın saat dilimi: geçmiş en son SAATLER saati (cron gecikmesine dayanır); yoksa None."""
    gecmis = [s for s in SAATLER if s <= simdi.hour]
    return gecmis[-1] if gecmis else None


def kuyruk_dosyasi(gun, saat):
    dosya = KUYRUK / f"{gun.isoformat()}-{saat:02d}00.json"
    eski = KUYRUK / f"{gun.isoformat()}.json"
    if not dosya.exists() and saat == 21 and eski.exists():
        return eski
    return dosya


def dilimde_paylasildi(token, baslangic, kenar="media"):
    """Son gönderi (ya da hikâye) bu dilimin başlangıcından sonraysa True (yeniden çalıştırmada çift paylaşımı önler)."""
    veri = istek(f"{HESAP}/{kenar}?fields=timestamp&limit=1", token).get("data", [])
    if not veri:
        return False
    son = datetime.strptime(veri[0]["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
    return son >= baslangic


def calistir(plan, token):
    kimlikler = []
    for yol, veri in plan:
        veri = {k: v.format(**{f"c{i}": c for i, c in enumerate(kimlikler)}) if k == "children" else v
                for k, v in veri.items()}
        kimlik = istek(yol, token, veri)["id"]
        bekle(kimlik, token)
        kimlikler.append(kimlik)
    return istek(f"{HESAP}/media_publish", token, {"creation_id": kimlikler[-1]})["id"]


def rapor(token):
    """Hesap ve son gönderilerin sayıları. Repo açık, log herkese açık: yorum metni ve kullanıcı adı yazdırılmaz."""
    h = istek(f"{HESAP}?fields=username,biography,followers_count,follows_count,media_count", token)
    print(f"hesap {h.get('username')}: {h.get('followers_count')} takipçi, {h.get('follows_count')} takip, "
          f"{h.get('media_count')} gönderi")
    print("bio:", json.dumps(h.get("biography", ""), ensure_ascii=False))
    hafta = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())
    try:
        hesap = istek(f"{HESAP}/insights?metric=reach,profile_views,accounts_engaged,follows_and_unfollows"
                      f"&period=day&metric_type=total_value&since={hafta}", token).get("data", [])
        print("son 7 gün:", ", ".join(f"{m['name']}={m.get('total_value', {}).get('value')}" for m in hesap))
    except Hata as ex:
        print("hesap insights alınamadı:", str(ex)[:120])
    medya = istek(f"{HESAP}/media?fields=id,timestamp,media_product_type,media_type,like_count,comments_count,caption"
                  "&limit=15", token).get("data", [])
    print("tarih | tür | beğeni | yorum | erişim | izlenme | kaydetme | paylaşım | medya_id | başlık")
    for m in medya:
        try:
            ins = {i["name"]: i["values"][0]["value"] for i in istek(
                f"{m['id']}/insights?metric=reach,views,saved,shares", token).get("data", [])}
        except Hata as ex:
            ins = {"reach": f"? ({str(ex)[:60]})"}
        baslik = (m.get("caption") or "").split("\n")[0][:40]
        print(" | ".join(str(x) for x in (m["timestamp"][:16], m.get("media_product_type"), m.get("like_count"),
              m.get("comments_count"), ins.get("reach", "-"), ins.get("views", "-"), ins.get("saved", "-"),
              ins.get("shares", "-"), m["id"], baslik)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="ağ isteği yapmadan planı yazdır")
    ap.add_argument("--tarih", help="YYYY-MM-DD (test)")
    ap.add_argument("--saat", type=int, help="0-23, TR saati (test)")
    ap.add_argument("--kontrol", action="store_true", help="yalnız token'ı dener, paylaşmaz")
    ap.add_argument("--rapor", action="store_true", help="hesap ve son gönderi sayılarını yazdırır, paylaşmaz")
    a = ap.parse_args()
    if not HESAP:
        raise Hata("IG_USER_ID tanımlı değil")
    if a.rapor:
        rapor(os.environ.get("IG_TOKEN", ""))
        return 0
    if a.kontrol:
        hesap = istek(f"{HESAP}?fields=username", os.environ.get("IG_TOKEN", ""))
        print("bağlantı tamam:", hesap.get("username"))
        izin = istek("me/permissions", os.environ.get("IG_TOKEN", "")).get("data", [])
        print("izinler:", ", ".join(i["permission"] for i in izin if i.get("status") == "granted"))
        return 0
    simdi = datetime.now(ISTANBUL)
    if a.tarih:
        simdi = datetime.strptime(a.tarih, "%Y-%m-%d").replace(hour=simdi.hour, tzinfo=ISTANBUL)
    if a.saat is not None:
        simdi = simdi.replace(hour=a.saat)
    saat = dilim(simdi)
    if saat is None:  # gece yarısını geçen gecikme: önceki günün son dilimi
        simdi, saat = simdi - timedelta(days=1), SAATLER[-1]
    print(f"::notice::dilim {simdi.date()} {saat:02d}:00")
    dosya = kuyruk_dosyasi(simdi.date(), saat)
    if not dosya.exists():
        print(f"::warning::kuyruk boş ({dosya.name})")
        return 0
    kayit = json.loads(dosya.read_text(encoding="utf-8"))
    pages = os.environ.get("PAGES_URL")
    if not pages:
        raise Hata("PAGES_URL tanımlı değil")
    plan = planla(kayit, pages)
    dosyalari_dogrula(kayit["dosyalar"])
    if a.kuru:
        for yol, veri in plan:
            print("POST", f"{API}/{yol}", json.dumps(veri, ensure_ascii=False))
        print("POST", f"{API}/{HESAP}/media_publish", '{"creation_id": "<son container>"}')
        return 0
    token = os.environ.get("IG_TOKEN")
    if not token:
        raise Hata("IG_TOKEN tanımlı değil")
    kenar = "stories" if kayit["tur"] == "hikaye" else "media"
    if dilimde_paylasildi(token, simdi.replace(hour=saat, minute=0, second=0, microsecond=0), kenar):
        print(f"{saat:02d}:00 dilimi zaten paylaşılmış")
        return 0
    print("yayınlandı:", calistir(plan, token))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Hata as ex:
        print("HATA:", temizle(ex), file=sys.stderr)
        sys.exit(1)
