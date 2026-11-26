"""İş birliği adayı mikro hesaplar: etiketlerin gönderilerinde ve tohum hesaplarda geçen @adları Business Discovery ile ölçer.
Yalnız okur, hiçbir şey paylaşmaz. Kullanım: IG_TOKEN=... IG_USER_ID=... python -X utf8 kesif.py --etiket ayet,dua --tohum hesap1"""
import argparse, os, re, sys, urllib.parse
from datetime import datetime, timezone

from paylas import HESAP, Hata, istek, temizle

AD = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{2,30})")
KONU = re.compile(r"ayet|dua|kur.?an|meal|hadis|allah|rabb|tefekk|hafız|sure|cuma|esma", re.I)
ALAN = ("business_discovery.username({}){{username,followers_count,biography,"
        "media.limit(12){{timestamp,like_count,comments_count,caption}}}}")
MIN_TAKIPCI, MAX_TAKIPCI, MAX_GUN, MAX_OLCUM = 5_000, 80_000, 14, 150  # Graph API: saatte ~200 çağrı


def etiket_adlari(etiket, token):
    hid = istek(f"ig_hashtag_search?user_id={HESAP}&q={urllib.parse.quote(etiket)}", token)["data"][0]["id"]
    adlar = set()
    for tur in ("top_media", "recent_media"):
        for m in istek(f"{hid}/{tur}?user_id={HESAP}&fields=caption&limit=50", token).get("data", []):
            adlar |= set(AD.findall(m.get("caption") or ""))
    return adlar


def olc(ad, token):
    b = istek(f"{HESAP}?fields={urllib.parse.quote(ALAN.format(ad), safe='(),{}')}", token)["business_discovery"]
    medya = b.get("media", {}).get("data", [])
    metin = " ".join([b.get("biography") or ""] + [m.get("caption") or "" for m in medya])
    son = max((datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")) for m in medya), default=None)
    ort = sum(m.get("like_count", 0) + m.get("comments_count", 0) for m in medya) / len(medya) if medya else 0
    return {"ad": b["username"], "takipci": b.get("followers_count", 0), "ort": ort,
            "gun": (datetime.now(timezone.utc) - son).days if son else 999,
            "konu": len(KONU.findall(metin)), "adlar": set(AD.findall(metin))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiket", default="ayet,kuranmeali,günündüası,dua,ayetler,tefekkür")
    ap.add_argument("--tohum", default="")
    a = ap.parse_args()
    token = os.environ.get("IG_TOKEN", "")
    if not HESAP or not token:
        raise Hata("IG_USER_ID / IG_TOKEN tanımlı değil")
    kuyruk = [t for t in (x.strip().lstrip("@") for x in a.tohum.split(",")) if re.fullmatch(r"[A-Za-z0-9_.]{2,30}", t)]
    for e in filter(None, (x.strip().lstrip("#") for x in a.etiket.split(","))):
        try:
            kuyruk += sorted(etiket_adlari(e, token))
        except (Hata, KeyError, IndexError) as ex:
            print(f"::warning::#{e}: {temizle(ex)[:150]}".replace("\n", " "))
    goruldu, sonuc, olculmedi = set(), [], 0
    while kuyruk and len(goruldu) < MAX_OLCUM:
        ad = kuyruk.pop(0).lower().rstrip(".")
        if ad in goruldu:
            continue
        goruldu.add(ad)
        try:
            h = olc(ad, token)
        except (Hata, KeyError) as ex:
            olculmedi += 1  # kişisel hesap ya da yok
            if any(k in str(ex).lower() for k in ("(#4)", "(#17)", "80004", "too many", "rate limit")):
                print("::warning::istek sınırı; erken bitti")
                break
            continue
        if h["konu"] >= 2:  # yalnız konu içi hesapların etiketledikleri kuyruğa
            kuyruk += sorted(h["adlar"] - goruldu)
            if MIN_TAKIPCI <= h["takipci"] <= MAX_TAKIPCI and h["gun"] <= MAX_GUN:
                sonuc.append(h)
    sonuc.sort(key=lambda h: h["ort"] / h["takipci"], reverse=True)
    print(f"ölçülen {len(goruldu)}, ölçülemeyen {olculmedi}, uygun {len(sonuc)}\n")
    print("| hesap | takipçi | ort. beğeni+yorum | etkileşim % | son paylaşım (gün) | konu |\n|---|---|---|---|---|---|")
    for h in sonuc:
        print(f"| [@{h['ad']}](https://instagram.com/{h['ad']}) | {h['takipci']:,} | {h['ort']:.0f} | "
              f"{100 * h['ort'] / h['takipci']:.1f} | {h['gun']} | {h['konu']} |")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Hata as ex:
        print("HATA:", temizle(ex), file=sys.stderr)
        sys.exit(1)
