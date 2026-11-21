"""Meta reklam planını uzlaştırır. Kullanım: META_ADS_TOKEN=... AD_ACCOUNT_ID=... FB_PAGE_ID=... IG_USER_ID=... python -X utf8 -I reklam.py [--kuru] [--rapor]
Plan: reklam/plan.json (şema: reklam/plan.sema.md). Sert sınırlar aşağıdaki sabitlerdedir; aşan plan reddedilir, hiçbir şey oluşturulmaz."""
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent
PLAN, DURUM = KOK / "reklam" / "plan.json", KOK / "reklam" / "durum.json"
ISTANBUL = timezone(timedelta(hours=3))

BUTCE_TL = float(os.environ.get("BUTCE_TL", "500"))
GUNLUK_TOPLAM_TL, TEK_REKLAM_GUN = 100, 7

# --- Meta API varsayımları: doğrulananlar ve [Varsayım] olanlar yalnız burada ---
API = "https://graph.facebook.com/v27.0"  # doğrulandı (use-posts-as-ads örnekleri v27.0)
MIN_GUNLUK_TL = 40  # [Varsayım] TRY min. günlük bütçe ~1 USD; hesapta farklıysa API reddeder
KURUS = 100  # [Varsayım] TRY için bütçe birimi kuruş (1/100)
# Creative alanları doğrulandı: object_id=sayfa, instagram_user_id, source_instagram_media_id.
# Hedefler: objective / optimization_goal / destination_type
#  profil_ziyareti: OUTCOME_TRAFFIC + PROFILE_VISIT + INSTAGRAM_PROFILE (Ad Set referansında enum var, topluluk API'de çalıştığını bildiriyor; [Varsayım] bu hesapta denenmedi)
#  etkilesim: OUTCOME_ENGAGEMENT + POST_ENGAGEMENT + ON_POST [Varsayım]
#  erisim: OUTCOME_AWARENESS + REACH, destination_type yok [Varsayım]
# Kampanya alanları is_adset_budget_sharing_enabled=false (bütçe adset'te), targeting_automation.advantage_audience=0 [Varsayım: v27'de zorunlu]
HEDEFLER = {
    "profil_ziyareti": ("OUTCOME_TRAFFIC", "PROFILE_VISIT", "INSTAGRAM_PROFILE"),
    "etkilesim": ("OUTCOME_ENGAGEMENT", "POST_ENGAGEMENT", "ON_POST"),
    "erisim": ("OUTCOME_AWARENESS", "REACH", None),
}
# Insights action_type adları [Varsayım]; bulunamazsa rapor "-" yazar
EYLEMLER = {"profil": ("instagram_profile_visits", "profile_visit"), "takip": ("follow", "onsite_conversion.ig_follow"),
            "kaydetme": ("onsite_conversion.post_save", "post_save")}

AD_RE = re.compile(r"^[a-z0-9-]{3,40}$")
DEGISEBILIR = ("gunluk_tl", "bitis", "durum")
SABIT = ("medya_id", "kuyruk", "hedef", "baslangic")


class Hata(Exception):
    pass


def temizle(metin):
    metin = re.sub(r"(access_token)=[^&\s\"']*", r"\1=***", str(metin))
    metin = re.sub(r"Bearer\s+\S+", "Bearer ***", metin)
    token = os.environ.get("META_ADS_TOKEN")
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


def gun(metin, alan):
    try:
        return date.fromisoformat(metin)
    except (TypeError, ValueError):
        raise Hata(f"{alan}: YYYY-MM-DD bekleniyor: {metin!r}") from None


def dogrula(plan, durum, bugun):
    """Sınırları denetler; ihlalde Hata. Bütçe: harcanan + kalan planlı <= BUTCE_TL; günlük toplam <= GUNLUK_TOPLAM_TL."""
    ogeler = plan.get("reklamlar")
    if not isinstance(ogeler, list):
        raise Hata("plan.json: 'reklamlar' liste olmalı")
    adlar, gunluk, kalan = set(), {}, 0.0
    for o in ogeler:
        ad = o.get("ad", "")
        if not AD_RE.match(ad) or ad in adlar:
            raise Hata(f"ad geçersiz ya da tekrar: {ad!r}")
        adlar.add(ad)
        if bool(o.get("medya_id")) == bool(o.get("kuyruk")):
            raise Hata(f"{ad}: medya_id ya da kuyruk (yalnız biri) gerekli")
        if o.get("hedef") not in HEDEFLER:
            raise Hata(f"{ad}: hedef {sorted(HEDEFLER)} içinden olmalı")
        if o.get("durum") not in ("aktif", "durdur"):
            raise Hata(f"{ad}: durum aktif|durdur olmalı")
        tl = o.get("gunluk_tl")
        if isinstance(tl, bool) or not isinstance(tl, (int, float)) or not MIN_GUNLUK_TL <= tl <= GUNLUK_TOPLAM_TL:
            raise Hata(f"{ad}: gunluk_tl {MIN_GUNLUK_TL}-{GUNLUK_TOPLAM_TL} arası sayı olmalı")
        bas, bit = gun(o.get("baslangic"), f"{ad}.baslangic"), gun(o.get("bitis"), f"{ad}.bitis")
        if bit < bas or (bit - bas).days + 1 > TEK_REKLAM_GUN:
            raise Hata(f"{ad}: süre 1-{TEK_REKLAM_GUN} gün olmalı")
        ymin, ymax = o.get("yas_min", 18), o.get("yas_max", 65)
        if not (isinstance(ymin, int) and isinstance(ymax, int) and 18 <= ymin <= ymax <= 65):
            raise Hata(f"{ad}: yaş aralığı 18-65 içinde olmalı")
        eski = durum["reklamlar"].get(ad)
        if eski:
            for k in SABIT:
                if k in eski["plan"] and eski["plan"][k] != o.get(k):
                    raise Hata(f"{ad}: {k} sonradan değişmez; yeni ad aç")
        if o["durum"] == "aktif":
            g = bas
            while g <= bit:
                gunluk[g] = gunluk.get(g, 0) + tl
                if g >= bugun:
                    kalan += tl
                g += timedelta(days=1)
    for g, t in sorted(gunluk.items()):
        if t > GUNLUK_TOPLAM_TL:
            raise Hata(f"{g}: günlük toplam {t} TL > {GUNLUK_TOPLAM_TL} TL")
    harcanan = sum(r.get("harcama_tl", 0) for r in durum["reklamlar"].values())
    if harcanan + kalan > BUTCE_TL:
        raise Hata(f"bütçe aşımı: harcanan {harcanan:.2f} + kalan planlı {kalan:.2f} > {BUTCE_TL:g} TL")


def zaman(g, ertesi_gun=False):
    return datetime.combine(g + timedelta(days=1 if ertesi_gun else 0), datetime.min.time(), ISTANBUL).isoformat()


def hedefleme(o):
    return {"geo_locations": {"countries": ["TR"]}, "age_min": o.get("yas_min", 18), "age_max": o.get("yas_max", 65),
            "publisher_platforms": ["instagram"], "targeting_automation": {"advantage_audience": 0}}


def medya_coz(o, token, ig):
    if o.get("medya_id"):
        return o["medya_id"]
    if token is None:
        return "<kuyruk gönderisinin id'si>"
    saat = datetime.strptime(o["kuyruk"], "%Y-%m-%d-%H%M").replace(tzinfo=ISTANBUL)
    for m in sorted(istek(f"{ig}/media?fields=id,timestamp&limit=25", token).get("data", []), key=lambda m: m["timestamp"]):
        t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if saat <= t <= saat + timedelta(hours=3):
            return m["id"]
    raise Hata(f"{o['ad']}: kuyruk {o['kuyruk']} için yayınlanmış gönderi bulunamadı")


def yeni_olustur(o, ctx, kayit, kaydet):
    """Önce PAUSED; her adımın id'si hemen durum.json'a yazılır, yarım kalırsa sonraki koşu kaldığı yerden sürer."""
    amac, hedef, hedef_tur = HEDEFLER[o["hedef"]]
    post, hesap = ctx["post"], f"act_{ctx['hesap']}"
    if "medya" not in kayit:
        kayit["medya"] = medya_coz(o, ctx["token"], ctx["ig"])
    if "kampanya" not in kayit:
        kayit["kampanya"] = post(f"{hesap}/campaigns", {
            "name": f"hal-{o['ad']}", "objective": amac, "status": "PAUSED", "special_ad_categories": "[]",
            "buying_type": "AUCTION", "is_adset_budget_sharing_enabled": "false"})["id"]
        kaydet()
    if "adset" not in kayit:
        baslangic = max(datetime.fromisoformat(zaman(gun(o["baslangic"], "baslangic"))), ctx["simdi"] + timedelta(minutes=5))
        veri = {"name": f"hal-{o['ad']}", "campaign_id": kayit["kampanya"], "status": "PAUSED",
                "daily_budget": int(round(o["gunluk_tl"] * KURUS)), "billing_event": "IMPRESSIONS",
                "optimization_goal": hedef, "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "start_time": baslangic.isoformat(), "end_time": zaman(gun(o["bitis"], "bitis"), True),
                "targeting": json.dumps(hedefleme(o)), "promoted_object": json.dumps({"page_id": ctx["sayfa"]})}
        if hedef_tur:
            veri["destination_type"] = hedef_tur
        kayit["adset"] = post(f"{hesap}/adsets", veri)["id"]
        kaydet()
    if "creative" not in kayit:
        kayit["creative"] = post(f"{hesap}/adcreatives", {
            "name": f"hal-{o['ad']}", "object_id": ctx["sayfa"], "instagram_user_id": ctx["ig"],
            "source_instagram_media_id": kayit["medya"]})["id"]
        kaydet()
    kayit["reklam"] = post(f"{hesap}/ads", {
        "name": f"hal-{o['ad']}", "adset_id": kayit["adset"], "creative": json.dumps({"creative_id": kayit["creative"]}),
        "status": "PAUSED"})["id"]
    kayit["durum_meta"] = "PAUSED"
    kaydet()


def uzlastir(plan, durum, ctx, kaydet):
    for o in plan["reklamlar"]:
        kayit = durum["reklamlar"].setdefault(o["ad"], {"plan": {}})
        if "reklam" not in kayit:
            if o["durum"] == "durdur" and "kampanya" not in kayit:
                del durum["reklamlar"][o["ad"]]
                print(f"{o['ad']}: durdur, oluşturulmadı")
                continue
            print(f"{o['ad']}: oluşturuluyor (PAUSED)")
            yeni_olustur(o, ctx, kayit, kaydet)
        elif kayit["plan"].get("gunluk_tl") != o["gunluk_tl"] or kayit["plan"].get("bitis") != o["bitis"]:
            print(f"{o['ad']}: bütçe/bitiş güncelleniyor")
            ctx["post"](kayit["adset"], {"daily_budget": int(round(o["gunluk_tl"] * KURUS)),
                                         "end_time": zaman(gun(o["bitis"], "bitis"), True)})
        hedef = "ACTIVE" if o["durum"] == "aktif" else "PAUSED"
        if kayit.get("durum_meta") != hedef:
            print(f"{o['ad']}: {hedef}")
            for yol in (kayit["reklam"], kayit["adset"], kayit["kampanya"]):
                ctx["post"](yol, {"status": hedef})
            kayit["durum_meta"] = hedef
        kayit["plan"] = {k: o.get(k) for k in (*SABIT, *DEGISEBILIR)}
        kaydet()


def eylem(satir, anahtarlar):
    for e in satir.get("actions", []):
        if e["action_type"] in anahtarlar:
            return e["value"]
    return "-"


def rapor(durum, token, kaydet):
    print("ad | durum | harcama TL | erişim | profil ziyareti | takip | kaydetme")
    for ad, k in durum["reklamlar"].items():
        if "reklam" not in k:
            continue
        veri = istek(f"{k['reklam']}/insights?fields=spend,reach,actions&date_preset=maximum", token).get("data", [])
        s = veri[0] if veri else {}
        k["harcama_tl"] = float(s.get("spend", 0))
        print(" | ".join(str(x) for x in (ad, k.get("durum_meta"), f"{k['harcama_tl']:.2f}", s.get("reach", "-"),
              eylem(s, EYLEMLER["profil"]), eylem(s, EYLEMLER["takip"]), eylem(s, EYLEMLER["kaydetme"]))))
    print(f"toplam harcama {sum(k.get('harcama_tl', 0) for k in durum['reklamlar'].values()):.2f} / {BUTCE_TL:g} TL")
    kaydet()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="ağsız; yapılacak çağrıları yazdır")
    ap.add_argument("--rapor", action="store_true", help="reklam başına sonuçları yazdır, durum.json'a harcamayı yaz")
    a = ap.parse_args()
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"reklamlar": {}}
    token = os.environ.get("META_ADS_TOKEN")
    ctx = {"hesap": os.environ.get("AD_ACCOUNT_ID", "").removeprefix("act_"), "sayfa": os.environ.get("FB_PAGE_ID", ""),
           "ig": os.environ.get("IG_USER_ID", ""), "token": token, "simdi": datetime.now(ISTANBUL)}
    if a.kuru:
        sayac = iter(range(1, 10**6))

        def post(yol, veri):
            print("POST", f"{API}/{yol}", json.dumps(veri, ensure_ascii=False))
            return {"id": f"<yeni-id-{next(sayac)}>"}
        kaydet = lambda: None
        ctx.update(token=None, hesap=ctx["hesap"] or "<AD_ACCOUNT_ID>", sayfa=ctx["sayfa"] or "<FB_PAGE_ID>",
                   ig=ctx["ig"] or "<IG_USER_ID>")
    else:
        if not (token and ctx["hesap"] and ctx["sayfa"] and ctx["ig"]):
            raise Hata("META_ADS_TOKEN, AD_ACCOUNT_ID, FB_PAGE_ID, IG_USER_ID tanımlı olmalı")
        post = lambda yol, veri: istek(yol, token, veri)
        kaydet = lambda: DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ctx["post"] = post
    if a.rapor:
        if a.kuru:
            print("rapor ağ gerektirir; --kuru ile atlandı")
            return 0
        rapor(durum, token, kaydet)
        return 0
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    dogrula(plan, durum, ctx["simdi"].date())
    print(f"plan geçerli: {len(plan['reklamlar'])} reklam")
    uzlastir(plan, durum, ctx, kaydet)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Hata as ex:
        print("::error::", temizle(ex))
        sys.exit(1)
