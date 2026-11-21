"""Instagram gönderileri (3:4, 1080x1440): meme karesi + ayet kartı + tanıtım.
Kullanım: python -X utf8 -I insta.py  (çıktı: medya/instagram/)"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import video as v  # noqa: E402  (font, ikon, içerik ve yardımcılar)

OUT = v.ROOT / "medya" / "instagram"
W, H = 1080, 1440
e = v.e
CSS = v.CSS.replace(f"width:{v.W}px;height:{v.H}px", f"width:{W}px;height:{H}px").replace(
    "padding:260px 130px 440px", "padding:120px 110px") + """
.meme{background:#fff;color:#111;font-family:'Segoe UI',Arial,sans-serif;justify-content:center;padding:110px}
.meme .t{font-size:62px;line-height:1.35;font-weight:600}
.meme .g{color:#8a8a8a;font-weight:500}
.meme .em{font-size:120px;margin-top:40px}
.bub{max-width:76%;font-size:50px;line-height:1.3;padding:26px 36px;border-radius:44px;margin:14px 0;font-weight:500}
.in{background:#E9E9EB;align-self:flex-start}.me{background:#0A84FF;color:#fff;align-self:flex-end}
.who{font-size:36px;color:#8a8a8a;text-align:center;margin-bottom:30px}
.notes{background:#FFFDF5}.notes .bar{color:#E0A100;font-size:40px;font-weight:600;margin-bottom:40px}
.notes .t{font-weight:500}
.bv{display:grid;grid-template-rows:1fr 1fr;gap:0;padding:0;height:100%}
.bv div{display:flex;flex-direction:column;justify-content:center;padding:0 110px}
.bv .lab{font-size:40px;letter-spacing:4px;color:#8a8a8a;font-weight:600;margin-bottom:20px}
.bv .b2{background:#111;color:#fff}
.swipe{position:fixed;bottom:70px;right:110px;font-size:38px;color:#8a8a8a;font-family:'Segoe UI',Arial,sans-serif}
"""
SW = '<div class="swipe">Kaydır →</div>'


def kimse(line, emoji=""):
    return ("meme", f'<div class="t"><span class="g">Kimse:</span><br><br>Ben {e(line)}</div>'
            + (f'<div class="em">{emoji}</div>' if emoji else "") + SW)


def chat(who, msgs):
    b = "".join(f'<div class="bub {"me" if me else "in"}">{e(t)}</div>' for me, t in msgs)
    return ("meme", f'<div class="who">{e(who)}</div>{b}{SW}')


def notes(title, lines):
    li = "<br>".join(e(x) for x in lines)
    return ("meme notes", f'<div class="bar">‹ Notlar</div><div class="t"><b>{e(title)}</b><br><br>{li}</div>{SW}')


def bv(beklenti, gercek):
    return ("meme bv", f'<div><div class="lab">BEKLENTİ</div><div class="t">{e(beklenti)}</div></div>'
            f'<div class="b2"><div class="lab">GERÇEK</div><div class="t">{e(gercek)}</div></div>{SW}')


def card(label, k):
    return ("", v.hal(label, k, True))


CTA = ("", v.CTA)

POSTS = {
    "1-gece-2": [kimse("gece 2'de: \"yarın her şeye yetişmem lazım, yetişemezsem ne olacak\"", "🫠"),
                 card("Zor bir gündeysen", "94:5"), CTA],
    "2-iyiyim": [chat("Annem", [(False, "Nasılsın?"), (True, "İyiyim anne 🙂"),
                                (False, "Sesin bir garip"), (True, "Yok yok, iyiyim")]),
                 card("Kendini yalnız hissediyorsan", "93:3"), CTA],
    "3-pazartesi": [bv("Bu hafta her şey yolunda gidecek.", "Pazartesi 09.12, ilk e‑posta."),
                    card("İçin daralıyorsa", "13:28"), CTA],
    "4-notlar": [notes("Bu ay içimden geçenler", ["1. Bir şey eksik gibi", "2. Ama ne?", "3. Dua etmek istiyorum",
                                                  "4. Nereden başlasam bilmiyorum"]),
                 card("Dua etmek istiyorsan", "2:186"), CTA],
    "5-bugun-nasilsin": [("", v.hook("Bugün nasılsın?", "Hâline göre bir ayet. Kaydır →")),
                         card("Zor bir gündeysen", "94:5"), card("İçin daralıyorsa", "13:28"),
                         card("Kendini yalnız hissediyorsan", "93:3"), card("Kaygılıysan", "65:3"), CTA],
}


def render(cls, body, png, tmp):
    f = tmp / (png.parent.name + png.stem + ".html")
    wm = "" if "meme" in cls else '<div class="wm" style="top:60px">HÂL</div>'
    f.write_text(f'<!doctype html><html lang=tr><meta charset=utf-8><style>{CSS}</style>'
                 f'<body class="{cls}">{wm}{body}</body>', encoding="utf-8")
    subprocess.run([v.CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--virtual-time-budget=5000", f"--window-size={W},{H}", f"--screenshot={png}", f.as_uri()],
                   check=True, capture_output=True, timeout=60)


if __name__ == "__main__":
    if OUT.exists():
        shutil.rmtree(OUT)
    with tempfile.TemporaryDirectory() as d:
        for name, slides in POSTS.items():
            (OUT / name).mkdir(parents=True)
            for i, (cls, body) in enumerate(slides, 1):
                render(cls, body, OUT / name / f"{i}.png", Path(d))
    shutil.copy(v.APP / "ios/Runner/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png", OUT / "profil-foto.png")
    print("ok")
