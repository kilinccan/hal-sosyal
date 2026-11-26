"""Yorum oyunu: yorum_veri.json'daki gönderilerin yorumlarına kelimeye uygun ayetle cevap verir.
Kullanım: IG_TOKEN=... IG_USER_ID=... python -X utf8 yorum.py [--kuru ornek_yorumlar.json]
Idempotent: bizim cevabımız olan yorum atlanır; durum dosyası yok. Loglarda kullanıcı adı/yorum metni/API gövdesi yok.
Kriz yorumları (intihar vb.) her filtre ve sınırdan önce, muaf olarak destek metni alır."""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse, zlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from paylas import HESAP, Hata, ISTANBUL, istek, temizle

BIZIM = "hal.uygulama"
VERI = Path(__file__).resolve().parent / "yorum_veri.json"
GUN, EN_UZUN_YORUM, ARA_SN, EN_COK_HATA = 7, 60, 3, 3
EN_COK_KOSU, EN_COK_GUN = 10, 40  # normal cevaplar; kriz cevapları muaf
SAYFA, EN_COK_SAYFA = 50, 5


class Durdur(Hata):
    """Kendi kontrollerimiz: mesajı güvenle yazdırılır (API gövdesi içermez)."""


# Crisis metni uygulamadaki Strings.crisisBody / crisisEmergency / crisisSocial ile birebir.
DESTEK = ("Yalnız değilsin. Kendine zarar vermeyi düşünüyorsan ya da çok zorlanıyorsan, bir uzmanla "
          "konuşabilirsin. Bu uygulama profesyonel destek yerine geçmez. Acil durum: 112 · "
          "Aile ve Sosyal Hizmetler: ALO 183 (7/24, ücretsiz) 🤍")

KRIZ = re.compile(
    r"intihar|suicide|\bkill myself|olmek (ist|en iyisi)|olmeyi ist|\bolsem|\bolum ist|umutsuz|dayanamiyo"
    r"|hayatim bitti|\bbittim\b|yok olmak|yok olsam|bilegimi|kendimi (oldur|kes|as|bitir|yak)"
    r"|kendime zarar|yasamak ist|yasamak yorul|yasamak zor|hayatima son|canima kiy|yasamayi birak|olup git|geber")
SPAM = re.compile(r"http|www\.|\.com|\.net|\.ly\b|@|#|t\.me|\bdm\b")
HAKARET = re.compile(
    r"\b(amk|aq|amina\w*|orospu\w*|siktir\w*|sikik\w*|sikeyim|yarrak\w*|yarak|pic|pezevenk|gavat|pust"
    r"|serefsiz|ibne|got\w*|salak|aptal|gerizekali|dangalak|oc|mal)\b")
NEGASYON = re.compile(r"\bdegil|m[iu]yor|amiyor|emiyor")
# Sıra önemli: ilk eşleşen ihtiyaç kazanır. Eşleşme yoksa cevap yok (genel liste yok).
ANAHTAR = (
    ("yorgun", r"\b(yorgun|bitkin|tukendi|tukenmis|halsiz|bikti|usandi)"),
    ("kaygi", r"\b(kaygi|endise|stres|gergin|panik|bunal|tedirgin|huzursuz|korku|korkuy|korkak|urper)"),
    ("uzgun", r"\b(uzgun|kirgin|mutsuz|huzun|keder|hasret|aglamak|aglad|caresiz|moralsiz|kirik)"),
    ("ofke", r"\b(ofke|sinir|kizgin|kiziyor|delir|bikkin)"),
    ("yalniz", r"\b(yalniz|ozlem|ozled|tek basima|yapayalniz)"),
    ("sabir", r"\bsabir"),
    ("umut", r"\b(umut|umit|dilek|temenni)"),
    ("sukur", r"\b(sukur|mutlu|huzurlu|minnet|iyiyim|iyi hissed|sevin|nese|memnun|alhamdulillah|elhamdulillah)"),
)
GIRIS = ("Hâline iyi gelsin:", "Sana bir ayet bırakalım:", "Gönlüne iyi gelsin:", "Bugün için bir ayet:")
TR = str.maketrans("âîûöüşçğı", "aiuouscgi")


def normalize(metin):
    m = metin.replace("İ", "i").replace("I", "ı").lower()
    m = unicodedata.normalize("NFC", m).translate(TR)
    return re.sub(r"\s+", " ", re.sub(r"[^\w@#.\s]", " ", m)).strip()


def ihtiyac(norm):
    """İhtiyaç adı; eşleşme yok ya da anahtar kelimeden sonra olumsuzlama varsa None."""
    for ad, kalip in ANAHTAR:
        m = re.search(kalip, norm)
        if m:
            return None if NEGASYON.search(norm[m.end():]) else ad
    return None


def cevap_metni(yorum, veri):
    """(ihtiyaç ya da 'kriz', cevap) ya da None (cevap yok). Kriz her filtreden önce, @'siz."""
    norm = normalize(yorum["text"])
    if KRIZ.search(norm):
        return "kriz", DESTEK
    if SPAM.search(norm) or len(yorum["text"]) > EN_UZUN_YORUM or HAKARET.search(norm):
        return None
    ad = ihtiyac(norm)
    if ad is None:
        return None
    liste = veri["ayetler"][ad]
    h = zlib.crc32(str(yorum["id"]).encode())
    a = liste[h % len(liste)]
    metin = f"@{yorum['username']} {GIRIS[(h // 7) % len(GIRIS)]} «{a['meal']}» ({a['sure']} {a['ayet']}) 🤍"
    if len(metin) > 300:
        raise Durdur(f"cevap 300 karakteri aşıyor: {ad} {a['sure']} {a['ayet']}")
    return ad, metin


def tarih(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def bugun(dt):
    return dt.astimezone(ISTANBUL).date()


def bizim_cevaplar(y):
    """Yorumun bizim cevaplarımız; username alanı yoksa güvenle ayırt edemeyiz, dur."""
    r = y.get("replies", {}).get("data", [])
    if any("username" not in x for x in r):
        raise Durdur("replies alanı username içermiyor, idempotentlik doğrulanamıyor")
    return [x for x in r if x["username"] == BIZIM]


def adaylar(yorumlar, simdi, baslangic):
    """Son 7 gün ve gönderi başlangıcından sonraki, bizden olmayan, bizce cevaplanmamış yorumlar."""
    sinir = simdi - timedelta(days=GUN)
    if baslangic:
        sinir = max(sinir, baslangic)
    return [y for y in yorumlar
            if y.get("username") != BIZIM and tarih(y["timestamp"]) >= sinir and not bizim_cevaplar(y)]


def bugunku_cevaplar(yorumlar, simdi):
    """(bugün bizim cevap sayısı, bugün cevap verdiğimiz kullanıcılar)."""
    n, kisiler = 0, set()
    for y in yorumlar:
        for r in bizim_cevaplar(y):
            if r.get("timestamp") and bugun(tarih(r["timestamp"])) == bugun(simdi):
                n += 1
                kisiler.add(y.get("username"))
    return n, kisiler


def kisalt(ex):
    """API hata gövdesi, yorum metni, kimlik ve kullanıcı adı olmadan: yalnız HTTP kodu + error.code."""
    s = str(ex)
    http = re.match(r"(\d{3}) ", s)
    kod = re.search(r'"code"\s*:\s*(\d+)', s)
    if not http:
        return "ağ hatası"
    return f"HTTP {http[1]}" + (f", kod {kod[1]}" if kod else "")


def yorumlari_al(medya, token):
    yorumlar, sonraki = [], None
    for _ in range(EN_COK_SAYFA):
        yol = f"{medya}/comments?fields=id,text,username,timestamp,replies%7Busername,timestamp%7D&limit={SAYFA}"
        if sonraki:
            yol += "&after=" + urllib.parse.quote(sonraki, safe="")
        s = istek(yol, token)
        yorumlar += [y for y in s.get("data", []) if y.get("text") and y.get("username")]
        sayfa = s.get("paging", {})
        sonraki = sayfa.get("cursors", {}).get("after") if sayfa.get("next") else None
        if not sonraki:
            break
    return yorumlar


def hesabi_dogrula(token):
    if not HESAP:
        raise Durdur("IG_USER_ID yok")
    kullanici = istek(f"{HESAP}?fields=username", token).get("username")
    if kullanici != BIZIM:
        raise Durdur("token beklenen hesaba ait değil")


def calistir(medyalar, veri, token, simdi, kuru):
    """medyalar: [(başlangıç ya da None, yorumlar)]. Kriz muaf; normal cevaplar koşu ve gün sınırlı."""
    sayac, hata, islenen = Counter(), 0, set()
    gun, kisiler = 0, set()
    for _, yorumlar in medyalar:
        n, k = bugunku_cevaplar(yorumlar, simdi)
        gun, kisiler = gun + n, kisiler | k
    plan = []
    for baslangic, yorumlar in medyalar:
        for y in adaylar(yorumlar, simdi, baslangic):
            if y["id"] in islenen:
                continue
            islenen.add(y["id"])
            sayac["aday"] += 1
            sonuc = cevap_metni(y, veri)
            if sonuc is None:
                sayac["atlandi"] += 1
            else:
                plan.append((y, *sonuc))
    plan.sort(key=lambda p: (p[1] != "kriz", p[0]["timestamp"]))
    normal = 0
    for y, ad, metin in plan:
        if ad != "kriz":
            if normal >= EN_COK_KOSU or gun >= EN_COK_GUN:
                sayac["sinir"] += 1
                continue
            if y["username"] in kisiler:
                sayac["atlandi"] += 1
                continue
        if not kuru:
            try:
                istek(f"{y['id']}/replies", token, {"message": metin})
            except Hata as ex:
                hata += 1
                print(f"cevap hatası: {kisalt(ex)}", file=sys.stderr)
                if hata >= EN_COK_HATA:
                    raise Durdur(f"{hata} cevap hatası, durduruldu") from None
                continue
            time.sleep(ARA_SN)
        gun += 1
        if ad != "kriz":
            normal += 1
            kisiler.add(y["username"])
        sayac["cevap"] += 1
        sayac[f"ihtiyac:{ad}"] += 1
    return sayac, hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", metavar="ORNEK_JSON", help="ağ isteği yapmadan, örnek yorumlarla planı yazdır")
    a = ap.parse_args()
    veri = json.loads(VERI.read_text(encoding="utf-8"))
    simdi = datetime.now(timezone.utc)
    try:
        if a.kuru:
            medyalar, token = [(None, json.loads(Path(a.kuru).read_text(encoding="utf-8")))], None
        else:
            token = os.environ.get("IG_TOKEN")
            if not token:
                raise Durdur("IG_TOKEN yok")
            if not veri["medyalar"]:
                print("medya yok, yapılacak iş yok")
                return 0
            hesabi_dogrula(token)
            medyalar = [(tarih(m["baslangic"]), yorumlari_al(m["id"], token)) for m in veri["medyalar"]]
        sayac, hata = calistir(medyalar, veri, token, simdi, bool(a.kuru))
    except Durdur as ex:
        print(f"HATA: {ex}", file=sys.stderr)
        return 1
    except Hata as ex:
        print(f"HATA: {kisalt(ex)}", file=sys.stderr)
        return 1
    print(("[kuru] " if a.kuru else "") + ", ".join(f"{k}={v}" for k, v in sorted(sayac.items())))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
