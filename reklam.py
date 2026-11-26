"""Meta reklam planını uzlaştırır. Kullanım: META_ADS_TOKEN=... AD_ACCOUNT_ID=... FB_PAGE_ID=... IG_USER_ID=... [VERI_KOKU=veri] python -X utf8 -I reklam.py [--kuru] [--rapor] [--ilgi-ara ARAMA]
Kod main'de, veri (reklam/plan.json, reklam/durum.json) VERI_KOKU altında (yayin dalı). Sert sınırlar aşağıdaki sabitlerdedir; aşan plan reddedilir, hiçbir şey oluşturulmaz.
Sıra: rapor (harcama Meta'dan) -> plan doğrulama -> uzlaştırma. --rapor yalnız raporu yapar."""
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERI = Path(os.environ.get("VERI_KOKU") or Path(__file__).resolve().parent)
PLAN, DURUM = VERI / "reklam" / "plan.json", VERI / "reklam" / "durum.json"
ISTANBUL = timezone(timedelta(hours=3))

BUTCE_TL = float(os.environ.get("BUTCE_TL", "500"))
GUNLUK_TOPLAM_TL, TEK_REKLAM_GUN = 100, 7
ASIM_PAYI = 1.25  # Meta günlük bütçeyi %25'e kadar aşabilir

# --- Meta API varsayımları: doğrulananlar ve [Varsayım] olanlar yalnız burada ---
API = "https://graph.facebook.com/v27.0"  # doğrulandı (use-posts-as-ads örnekleri v27.0)
MIN_GUNLUK_TL = 40  # [Varsayım] TRY min. günlük bütçe ~1 USD; hesapta farklıysa API reddeder
KURUS = 100  # [Varsayım] TRY için bütçe birimi kuruş (1/100)
# Creative alanları doğrulandı: object_id=sayfa, instagram_user_id, source_instagram_media_id.
# Hedefler: objective / optimization_goal / destination_type
#  profil_ziyareti: OUTCOME_TRAFFIC + PROFILE_VISIT + INSTAGRAM_PROFILE (Ad Set referansında enum var, topluluk API'de çalıştığını bildiriyor; [Varsayım] bu hesapta denenmedi)
#  etkilesim: OUTCOME_ENGAGEMENT + POST_ENGAGEMENT + ON_POST [Varsayım]
#  erisim: OUTCOME_AWARENESS + REACH, destination_type yok [Varsayım]
#  app_store: OUTCOME_TRAFFIC + LINK_CLICKS + WEBSITE; creative call_to_action DOWNLOAD + link (2061015 "link zorunlu" hatası
#   profil_ziyareti'nde görüldü). Link kendi indirme sayfamız: Meta App Store linkini yalnız App Installs hedefinde kabul
#   ediyor (26 Kas Delivery error); sayfadaki buton App Store'a gider.
# [Varsayım] is_adset_budget_sharing_enabled=false (bütçe adset'te), targeting_automation.advantage_audience=0, campaigns?filtering EQUAL operatörü
HEDEFLER = {
    "profil_ziyareti": ("OUTCOME_TRAFFIC", "PROFILE_VISIT", "INSTAGRAM_PROFILE"),
    "etkilesim": ("OUTCOME_ENGAGEMENT", "POST_ENGAGEMENT", "ON_POST"),
    "erisim": ("OUTCOME_AWARENESS", "REACH", None),
    "app_store": ("OUTCOME_TRAFFIC", "LINK_CLICKS", "WEBSITE"),
}
APP_STORE_RE = re.compile(r"^https://kilinccan\.github\.io/hal/(\?[A-Za-z0-9=&_.-]*)?$")
# Insights action_type adları [Varsayım]; bulunamazsa rapor "-" yazar
EYLEMLER = {"profil": ("instagram_profile_visits", "profile_visit"), "takip": ("follow", "onsite_conversion.ig_follow"),
            "kaydetme": ("onsite_conversion.post_save", "post_save")}

AD_RE = re.compile(r"^[a-z0-9-]{3,40}$")
SAYI_RE = re.compile(r"^\d+$")
KUYRUK_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}$")
DEGISEBILIR = ("gunluk_tl", "bitis", "durum")
SABIT = ("medya_id", "kuyruk", "hedef", "baslangic", "link", "ilgi")
ILGI_EN = 10
KIMLIKLER = ("medya", "kampanya", "adset", "creative", "reklam")


class Hata(Exception):
    pass


def temizle(metin):
    metin = re.sub(r"(access_token)=[^&\s\"']*", r"\1=***", str(metin))
    metin = re.sub(r"Bearer\s+\S+", "Bearer ***", metin)
    metin = re.sub(r"act_\d+", "act_***", metin)
    for ad in ("META_ADS_TOKEN", "AD_ACCOUNT_ID", "FB_PAGE_ID", "IG_USER_ID"):
        deger = os.environ.get(ad)
        if deger:
            metin = metin.replace(deger, "***")
    return metin


def meta_hatasi(ex):
    """Meta hatasından code, alt kod, message, başlık ve suçlanan alan adları; tek satır, en çok 300 karakter.
    Log herkese açık: error_user_msg yazılmaz; satır sonu workflow komutu enjekte edemesin diye silinir."""
    try:
        e = json.loads(ex.read(65536).decode("utf-8", "replace"))["error"]
        parcalar = [f"code={e.get('code')} {e.get('message')}"]
        if e.get("error_subcode"):
            parcalar.append(f"subcode={e['error_subcode']}")
        if e.get("error_user_title"):
            parcalar.append(str(e["error_user_title"]))
        # error_data bazen nesne, bazen JSON metni: ikisinde de yalnız alan adları alınır
        veri = e.get("error_data")
        veri = veri if isinstance(veri, str) else json.dumps(veri)
        blok = re.search(r'"blame_field_specs"\s*:\s*(\[\[.*?\]\])', veri)
        alanlar = re.findall(r'"([a-z_]{3,40})"', blok.group(1)) if blok else []
        if alanlar:
            parcalar.append(f"alan={','.join(alanlar)}")
        return " ".join(" | ".join(parcalar).split())[:300]
    except (ValueError, KeyError, TypeError, AttributeError):
        return "gövde okunamadı"


def istek(yol, token, veri=None):
    """veri verilirse POST (gövde), yoksa GET; token yalnız Authorization başlığında."""
    gövde = urllib.parse.urlencode(veri).encode() if veri is not None else None
    r = urllib.request.Request(f"{API}/{yol}", data=gövde, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(r, timeout=60) as y:
            return json.load(y)
    except urllib.error.HTTPError as ex:
        raise Hata(temizle(f"HTTP {ex.code} {yol.split('?')[0]}: {meta_hatasi(ex)}")) from None
    except urllib.error.URLError as ex:
        raise Hata(temizle(f"{yol.split('?')[0]}: {ex.reason}")) from None


def kimlik(deger, alan):
    if not isinstance(deger, str) or not SAYI_RE.match(deger):
        raise Hata(f"{alan}: yalnız rakam olmalı")
    return deger


def gun(metin, alan):
    try:
        return date.fromisoformat(metin)
    except (TypeError, ValueError):
        raise Hata(f"{alan}: YYYY-MM-DD bekleniyor: {metin!r}") from None


def dogrula(plan, durum, bugun, harcanan):
    """Sınırları denetler; ihlalde Hata. Bütçe: harcanan + kalan planlı x ASIM_PAYI <= BUTCE_TL; günlük toplam <= GUNLUK_TOPLAM_TL."""
    ogeler = plan.get("reklamlar") if isinstance(plan, dict) else None
    if not isinstance(ogeler, list):
        raise Hata("plan.json: 'reklamlar' liste olmalı")
    adlar, gunluk, kalan = set(), {}, 0.0
    for o in ogeler:
        if not isinstance(o, dict):
            raise Hata("plan.json: her öğe nesne olmalı")
        ad = o.get("ad", "")
        if not isinstance(ad, str) or not AD_RE.match(ad) or ad in adlar:
            raise Hata(f"ad geçersiz ya da tekrar: {ad!r}")
        adlar.add(ad)
        medya, kuyruk = o.get("medya_id"), o.get("kuyruk")
        if bool(medya) == bool(kuyruk):
            raise Hata(f"{ad}: medya_id ya da kuyruk (yalnız biri) gerekli")
        if medya:
            kimlik(medya, f"{ad}.medya_id")
        elif not isinstance(kuyruk, str) or not KUYRUK_RE.match(kuyruk):
            raise Hata(f"{ad}: kuyruk YYYY-MM-DD-HHMM olmalı")
        if o.get("hedef") not in HEDEFLER:
            raise Hata(f"{ad}: hedef {sorted(HEDEFLER)} içinden olmalı")
        link = o.get("link")
        if (o["hedef"] == "app_store") != (link is not None):
            raise Hata(f"{ad}: link yalnız ve zorunlu olarak app_store hedefinde")
        if link is not None and (not isinstance(link, str) or not APP_STORE_RE.match(link)):
            raise Hata(f"{ad}: link indirme sayfası (https://kilinccan.github.io/hal/) olmalı")
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
        if "ilgi" in o:
            ilgi_dogrula(o["ilgi"], ad)
        eski = durum["reklamlar"].get(ad)
        if eski:
            for k in SABIT:
                if eski["plan"].get(k) != o.get(k):  # eski kayıtta olmayan alan (ilgi) sonradan eklenemez
                    raise Hata(f"{ad}: {k} sonradan değişmez; yeni ad aç")
        elif o["durum"] == "aktif" and bit < bugun:
            raise Hata(f"{ad}: bitis geçmişte")
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
    if harcanan + kalan * ASIM_PAYI > BUTCE_TL:
        raise Hata(f"bütçe aşımı: harcanan {harcanan:.2f} + kalan planlı {kalan:.2f} x {ASIM_PAYI} > {BUTCE_TL:g} TL")


def ilgi_dogrula(ilgi, ad):
    if not isinstance(ilgi, list) or not 1 <= len(ilgi) <= ILGI_EN:
        raise Hata(f"{ad}: ilgi 1-{ILGI_EN} öğeli liste olmalı")
    for i in ilgi:
        if not (isinstance(i, dict) and set(i) == {"id", "name"} and isinstance(i["name"], str) and i["name"].strip()):
            raise Hata(f'{ad}: ilgi öğesi {{"id": "...", "name": "..."}} olmalı')
        kimlik(i["id"], f"{ad}.ilgi.id")


def durum_dogrula(durum):
    if not isinstance(durum, dict) or not isinstance(durum.get("reklamlar"), dict):
        raise Hata("durum.json: 'reklamlar' nesne olmalı")
    for ad, k in durum["reklamlar"].items():
        if not isinstance(k, dict) or not isinstance(k.get("plan"), dict):
            raise Hata(f"durum.json: {ad} bozuk")
        for alan in KIMLIKLER:
            if alan in k:
                kimlik(k[alan], f"durum.json {ad}.{alan}")


def zaman(g, ertesi_gun=False):
    return datetime.combine(g + timedelta(days=1 if ertesi_gun else 0), datetime.min.time(), ISTANBUL).isoformat()


def hedefleme(o):
    t = {"geo_locations": {"countries": ["TR"]}, "age_min": o.get("yas_min", 18), "age_max": o.get("yas_max", 65),
            "publisher_platforms": ["instagram"], "device_platforms": ["mobile"], "user_os": ["iOS"],
            "targeting_automation": {"advantage_audience": 0}}
    if o.get("ilgi"):
        t["flexible_spec"] = [{"interests": [{"id": i["id"], "name": i["name"]} for i in o["ilgi"]]}]
    return t


def ilgi_ara(arama, token):
    """Yalnız okur: Meta ilgi alanı kimliklerini listeler; plan.json'a elle kopyalanır."""
    q = urllib.parse.urlencode({"type": "adinterest", "q": arama, "locale": "tr_TR", "limit": 25})
    for d in istek(f"search?{q}", token).get("data", []):
        print(temizle(f"{d.get('id')}	{d.get('name')}	{d.get('audience_size_lower_bound')}"))


def medya_coz(o, ctx):
    if o.get("medya_id"):
        return o["medya_id"]
    if ctx["token"] is None:
        return "<kuyruk gönderisinin id'si>"
    saat = datetime.strptime(o["kuyruk"], "%Y-%m-%d-%H%M").replace(tzinfo=ISTANBUL)
    for m in sorted(ctx["al"](f"{ctx['ig']}/media?fields=id,timestamp&limit=25").get("data", []), key=lambda m: m["timestamp"]):
        t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if saat <= t <= saat + timedelta(hours=3):
            return m["id"]
    raise Hata(f"{o['ad']}: kuyruk {o['kuyruk']} için yayınlanmış gönderi bulunamadı")


def mevcut(ctx, yol, ad=None):
    """Meta'da zaten var olan nesne (durum.json kaybına karşı idempotentlik)."""
    for d in ctx["al"](yol).get("data", []):
        if ad is None or d.get("name") == ad:
            return d
    return None


def yeni_olustur(o, ctx, kayit, kaydet):
    """Önce PAUSED; her adımın id'si hemen durum.json'a yazılır, yarım kalırsa sonraki koşu kaldığı yerden sürer.
    Meta'da hal-<ad> kampanyası varsa yeniden üretmek yerine o kullanılır."""
    amac, hedef, hedef_tur = HEDEFLER[o["hedef"]]
    post, hesap, ad = ctx["post"], f"act_{ctx['hesap']}", f"hal-{o['ad']}"
    olusturuldu = False
    if "medya" not in kayit:
        kayit["medya"] = medya_coz(o, ctx)
    if "kampanya" not in kayit:
        filtre = urllib.parse.quote(json.dumps([{"field": "name", "operator": "EQUAL", "value": ad}]))
        m = mevcut(ctx, f"{hesap}/campaigns?fields=id,name&filtering={filtre}", ad)
        if m:
            kayit["kampanya"] = m["id"]
        else:
            kayit["kampanya"] = post(f"{hesap}/campaigns", {
                "name": ad, "objective": amac, "status": "PAUSED", "special_ad_categories": "[]",
                "buying_type": "AUCTION", "is_adset_budget_sharing_enabled": "false"})["id"]
            olusturuldu = True
        kaydet()
    if "adset" not in kayit:
        m = None if olusturuldu else mevcut(ctx, f"{kayit['kampanya']}/adsets?fields=id")
        if m:
            kayit["adset"] = m["id"]
        else:
            baslangic = max(datetime.fromisoformat(zaman(gun(o["baslangic"], "baslangic"))), ctx["simdi"] + timedelta(minutes=5))
            veri = {"name": ad, "campaign_id": kayit["kampanya"], "status": "PAUSED",
                    "daily_budget": int(round(o["gunluk_tl"] * KURUS)), "billing_event": "IMPRESSIONS",
                    "optimization_goal": hedef, "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    "start_time": baslangic.isoformat(), "end_time": zaman(gun(o["bitis"], "bitis"), True),
                    "targeting": json.dumps(hedefleme(o)), "promoted_object": json.dumps({"page_id": ctx["sayfa"]})}
            if hedef_tur:
                veri["destination_type"] = hedef_tur
            kayit["adset"] = post(f"{hesap}/adsets", veri)["id"]
            olusturuldu = True
        kaydet()
    if "reklam" not in kayit and not olusturuldu:
        m = mevcut(ctx, f"{kayit['adset']}/ads?fields=id,creative%7Bid%7D")
        if m:
            kayit["reklam"] = m["id"]
            kayit["creative"] = (m.get("creative") or {}).get("id") or kayit.get("creative")
            kaydet()
            return
    if "creative" not in kayit:
        veri = {"name": ad, "object_id": ctx["sayfa"], "instagram_user_id": ctx["ig"],
                "source_instagram_media_id": kayit["medya"]}
        if o.get("link"):
            veri["call_to_action"] = json.dumps({"type": "DOWNLOAD", "value": {"link": o["link"]}})
        kayit["creative"] = post(f"{hesap}/adcreatives", veri)["id"]
        kaydet()
    kayit["reklam"] = post(f"{hesap}/ads", {
        "name": ad, "adset_id": kayit["adset"], "creative": json.dumps({"creative_id": kayit["creative"]}),
        "status": "PAUSED"})["id"]
    kayit["durum_meta"] = "PAUSED"
    kaydet()


def durum_ver(ctx, kayit, hedef):
    for yol in (kayit["reklam"], kayit["adset"], kayit["kampanya"]):
        ctx["post"](yol, {"status": hedef})
    kayit["durum_meta"] = hedef


def uzlastir(plan, durum, ctx, kaydet):
    planda = set()
    for o in plan["reklamlar"]:
        planda.add(o["ad"])
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
            durum_ver(ctx, kayit, hedef)
        kayit["plan"] = {k: o.get(k) for k in (*SABIT, *DEGISEBILIR)}
        kaydet()
    for ad, kayit in durum["reklamlar"].items():
        if ad not in planda and "reklam" in kayit and kayit.get("durum_meta") != "PAUSED":
            print(f"{ad}: planda yok, PAUSED")
            durum_ver(ctx, kayit, "PAUSED")
            kaydet()


def eylem(satir, anahtarlar):
    for e in satir.get("actions", []):
        if e["action_type"] in anahtarlar:
            return e["value"]
    return "-"


def hesap_harcamasi(ctx):
    veri = ctx["al"](f"act_{ctx['hesap']}/insights?fields=spend&date_preset=maximum").get("data", [])
    return float(veri[0].get("spend", 0)) if veri else 0.0


def rapor(durum, ctx, kaydet):
    """Hesabın toplam harcamasını (sınırın tek kaynağı) döndürür; reklam başına satırlar bilgi amaçlı."""
    print("ad | durum | harcama TL | erişim | profil ziyareti | takip | kaydetme")
    for ad, k in durum["reklamlar"].items():
        if "reklam" not in k:
            continue
        veri = ctx["al"](f"{k['reklam']}/insights?fields=spend,reach,actions&date_preset=maximum").get("data", [])
        s = veri[0] if veri else {}
        k["harcama_tl"] = float(s.get("spend", 0))
        print(" | ".join(str(x) for x in (ad, k.get("durum_meta"), f"{k['harcama_tl']:.2f}", s.get("reach", "-"),
              eylem(s, EYLEMLER["profil"]), eylem(s, EYLEMLER["takip"]), eylem(s, EYLEMLER["kaydetme"]))))
    toplam = hesap_harcamasi(ctx)
    print(f"hesap toplam harcama {toplam:.2f} / {BUTCE_TL:g} TL")
    kaydet()
    return toplam


def baglam(kuru):
    ctx = {"hesap": os.environ.get("AD_ACCOUNT_ID", "").removeprefix("act_"), "sayfa": os.environ.get("FB_PAGE_ID", ""),
           "ig": os.environ.get("IG_USER_ID", ""), "token": os.environ.get("META_ADS_TOKEN"), "simdi": datetime.now(ISTANBUL)}
    if kuru:
        sayac = iter(range(1, 10**6))

        def post(yol, veri):
            print("POST", temizle(f"{API}/{yol}"), temizle(json.dumps(veri, ensure_ascii=False)))
            return {"id": f"<yeni-id-{next(sayac)}>"}
        ctx.update(token=None, post=post, al=lambda yol: {"data": []},
                   hesap=ctx["hesap"] or "<AD_ACCOUNT_ID>", sayfa=ctx["sayfa"] or "<FB_PAGE_ID>", ig=ctx["ig"] or "<IG_USER_ID>")
        return ctx
    if not (ctx["token"] and ctx["hesap"] and ctx["sayfa"] and ctx["ig"]):
        raise Hata("META_ADS_TOKEN, AD_ACCOUNT_ID, FB_PAGE_ID, IG_USER_ID tanımlı olmalı")
    for alan in ("hesap", "sayfa", "ig"):
        kimlik(ctx[alan], alan)

    def al(yol):
        r = istek(yol, ctx["token"])
        for d in r.get("data", []):
            if "id" in d:
                kimlik(d["id"], "Meta yanıtı id")
        return r

    def post(yol, veri):
        r = istek(yol, ctx["token"], veri)
        if "id" in r:
            kimlik(r["id"], "Meta yanıtı id")
        return r
    ctx.update(post=post, al=al)
    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="ağsız; yapılacak çağrıları yazdır")
    ap.add_argument("--rapor", action="store_true", help="yalnız rapor; durum.json'a harcamayı yazar")
    ap.add_argument("--ilgi-ara", metavar="ARAMA", help="yalnız ilgi alanı kimliği ara; hiçbir şey oluşturmaz")
    a = ap.parse_args()
    if a.ilgi_ara:
        if not os.environ.get("META_ADS_TOKEN"):
            raise Hata("META_ADS_TOKEN tanımlı olmalı")
        ilgi_ara(a.ilgi_ara, os.environ["META_ADS_TOKEN"])
        return 0
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"reklamlar": {}}
    durum_dogrula(durum)
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if not a.rapor and not a.kuru and isinstance(plan, dict) and plan.get("reklamlar") == [] and not durum["reklamlar"] \
            and not os.environ.get("META_ADS_TOKEN"):
        print("plan boş, yapılacak iş yok")
        return 0
    ctx = baglam(a.kuru)
    kaydet = (lambda: None) if a.kuru else (lambda: DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"))
    if a.kuru:
        print("rapor ağ gerektirir; --kuru ile atlandı, harcanan 0 sayıldı")
        harcanan = 0.0
    else:
        harcanan = rapor(durum, ctx, kaydet)
    if a.rapor:
        return 0
    dogrula(plan, durum, ctx["simdi"].date(), harcanan)
    print(f"plan geçerli: {len(plan['reklamlar'])} reklam")
    uzlastir(plan, durum, ctx, kaydet)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Hata, ValueError, TypeError, KeyError) as ex:
        print("::error::", temizle(ex if isinstance(ex, Hata) else f"{type(ex).__name__}: {ex}"))
        sys.exit(1)
