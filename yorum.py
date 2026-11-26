"""Yorum oyunu: yorum_veri.json'daki gönderilerin yorumlarına kelimeye uygun ayetle cevap verir.
Kullanım: IG_TOKEN=... IG_USER_ID=... python -X utf8 yorum.py [--kuru ornek_yorumlar.json]
Idempotent: bizim cevabımız olan yorum atlanır; durum dosyası yok. Loglarda kullanıcı adı/yorum metni yok."""
import argparse, json, os, re, sys, time, unicodedata, zlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from paylas import Hata, ISTANBUL, istek, temizle

BIZIM = "hal.uygulama"
VERI = Path(__file__).resolve().parent / "yorum_veri.json"
GUN, EN_UZUN_YORUM, EN_COK_CEVAP, ARA_SN, EN_COK_HATA = 7, 60, 30, 3, 3
SAYFA, EN_COK_SAYFA = 50, 5

# Crisis metni uygulamadaki Strings.crisisBody / crisisEmergency / crisisSocial ile birebir.
DESTEK = ("Yalnız değilsin. Kendine zarar vermeyi düşünüyorsan ya da çok zorlanıyorsan, bir uzmanla "
          "konuşabilirsin. Bu uygulama profesyonel destek yerine geçmez. Acil durum: 112 · "
          "Aile ve Sosyal Hizmetler: ALO 183 (7/24, ücretsiz) 🤍")

KRIZ = re.compile(r"intihar|olmek ist|kendime zarar|kendimi (oldur|kes|as)|yasamak ist|yasamak yorul|hayatima son|canima kiy|olsem")
SPAM = re.compile(r"http|www\.|\.com|\.net|\.ly\b|@|#|t\.me|\bdm\b")
HAKARET = re.compile(r"\b(amk|aq|orospu|siktir|sik[ei]|piç|pic|yarrak|got\w*|salak|aptal|gerizekali|ibne)\b")
# Sıra önemli: ilk eşleşen ihtiyaç kazanır. "iyi degilim" şükürden önce üzgüne düşer.
ANAHTAR = (
    ("yorgun", r"\b(yorgun|bitkin|tukendi|tukenmis|bitti|halsiz|bikti|usandi)"),
    ("kaygi", r"\b(kaygi|endise|stres|gergin|panik|bunal|tedirgin|huzursuz)"),
    ("uzgun", r"\b(uzgun|kirgin|mutsuz|huzun|keder|hasret|aglamak|aglad|caresiz|moralsiz|kirik|iyi degil)"),
    ("ofke", r"\b(ofke|sinir|kizgin|kiziyor|delir|bikkin)"),
    ("korku", r"\b(korku|korkuy|korkak|urper)"),
    ("yalniz", r"\b(yalniz|ozlem|ozled|tek basima|yapayalniz)"),
    ("sabir", r"\bsabir"),
    ("umut", r"\b(umut|umit|dilek|temenni)"),
    ("sukur", r"\b(sukur|mutlu|huzurlu|minnet|iyiyim|iyi|sevin|nese|memnun|alhamdulillah|elhamdulillah)"),
)
TR = str.maketrans("âîûöüşçğı", "aiuouscgi")


def normalize(metin):
    m = metin.replace("İ", "i").replace("I", "ı").lower()
    m = unicodedata.normalize("NFC", m).translate(TR)
    return re.sub(r"\s+", " ", re.sub(r"[^\w@#.\s]", " ", m)).strip()


def ihtiyac(norm):
    for ad, kalip in ANAHTAR:
        if re.search(kalip, norm):
            return ad
    return "genel"


def cevap_metni(yorum, veri):
    """(ihtiyaç ya da 'kriz', cevap) ya da None (cevap yok)."""
    norm = normalize(yorum["text"])
    if SPAM.search(norm):
        return None
    kullanici = f"@{yorum['username']}"
    if KRIZ.search(norm):
        return "kriz", f"{kullanici} {DESTEK}"
    if len(yorum["text"]) > EN_UZUN_YORUM or HAKARET.search(norm):
        return None
    ad = ihtiyac(norm)
    liste = veri["ayetler"][ad]
    a = liste[zlib.crc32(str(yorum["id"]).encode()) % len(liste)]
    metin = f"{kullanici} Hâline iyi gelsin: «{a['meal']}» ({a['sure']} {a['ayet']}) 🤍"
    if len(metin) > 300:
        raise Hata(f"cevap 300 karakteri aşıyor: {ad} {a['sure']} {a['ayet']}")
    return ad, metin


def tarih(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def bugun(simdi):
    return simdi.astimezone(ISTANBUL).date()


def secilenler(yorumlar, simdi):
    """Cevaplanacak yorumlar: son 7 gün, bizden değil, cevaplanmamış, kişi başına günde bir."""
    sinir = simdi - timedelta(days=GUN)
    cevaplananlar = {(y["username"], bugun(tarih(r["timestamp"])))
                     for y in yorumlar for r in y.get("replies", {}).get("data", [])
                     if r.get("username") == BIZIM and r.get("timestamp")}
    secilen = []
    for y in sorted(yorumlar, key=lambda y: y["timestamp"]):
        if y.get("username") == BIZIM or tarih(y["timestamp"]) < sinir:
            continue
        if any(r.get("username") == BIZIM for r in y.get("replies", {}).get("data", [])):
            continue
        anahtar = (y["username"], bugun(simdi))
        if anahtar in cevaplananlar:
            continue
        cevaplananlar.add(anahtar)
        secilen.append(y)
    return secilen


def yorumlari_al(medya, token):
    yorumlar, sonraki = [], None
    for _ in range(EN_COK_SAYFA):
        yol = f"{medya}/comments?fields=id,text,username,timestamp,replies%7Busername,timestamp%7D&limit={SAYFA}"
        if sonraki:
            yol += f"&after={sonraki}"
        s = istek(yol, token)
        yorumlar += [y for y in s.get("data", []) if y.get("text") and y.get("username")]
        sonraki = s.get("paging", {}).get("cursors", {}).get("after") if s.get("paging", {}).get("next") else None
        if not sonraki:
            break
    return yorumlar


def calistir(yorumlar_by_medya, veri, token, simdi, kuru):
    sayac, hata = Counter(), 0
    for yorumlar in yorumlar_by_medya:
        sec = secilenler(yorumlar, simdi)
        sayac["aday"] += len(sec)
        for y in sec:
            if sayac["cevap"] >= EN_COK_CEVAP:
                sayac["sinir"] += 1
                continue
            sonuc = cevap_metni(y, veri)
            if sonuc is None:
                sayac["atlandi"] += 1
                continue
            ad, metin = sonuc
            if not kuru:
                try:
                    istek(f"{y['id']}/replies", token, {"message": metin})
                except Hata as ex:
                    hata += 1
                    print(f"cevap hatası: {temizle(str(ex))[:200]}", file=sys.stderr)
                    if hata >= EN_COK_HATA:
                        raise Hata(f"{hata} cevap hatası, durduruldu") from None
                    continue
                time.sleep(ARA_SN)
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
            yorumlar = [json.loads(Path(a.kuru).read_text(encoding="utf-8"))]
            token = None
        else:
            token = os.environ.get("IG_TOKEN")
            if not token:
                raise Hata("IG_TOKEN yok")
            if not veri["medyalar"]:
                print("medya yok, yapılacak iş yok")
                return 0
            yorumlar = [yorumlari_al(m, token) for m in veri["medyalar"]]
        sayac, hata = calistir(yorumlar, veri, token, simdi, bool(a.kuru))
    except Hata as ex:
        print(f"HATA: {temizle(str(ex))}", file=sys.stderr)
        return 1
    print(("[kuru] " if a.kuru else "") + ", ".join(f"{k}={v}" for k, v in sorted(sayac.items())))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
