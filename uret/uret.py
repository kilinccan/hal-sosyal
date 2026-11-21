import json, os, subprocess, shutil, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("HAL_APP") or ROOT.parent / "ckappdesign" / "app")
OUT = ROOT / "medya" / "tiktok"
TMP = Path(sys.argv[1])
CHROME = os.environ.get("CHROME", "C:/Program Files/Google/Chrome/Application/chrome.exe")
W, H = 1080, 1920

items = {x["translation_key"]: x for x in json.load(open(APP / "assets/content/items.json", encoding="utf-8"))}
meal = json.load(open(APP / "assets/content/meal/elmalili.json", encoding="utf-8"))["texts"]
import base64
F=lambda n:'data:font/ttf;base64,'+base64.b64encode((APP/'assets/fonts'/n).read_bytes()).decode()
ICON = (APP / "ios/Runner/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png").as_uri()


def ref(k):
    x = items[k]
    a = str(x["ayah"]) +(f"-{x['ayah_end']}" if x.get("ayah_end") else "")
    return f"{x['surah_name']} {x['surah']}:{a}"


CSS = f"""
@font-face{{font-family:HalSerif;src:url({F('SourceSerif4.ttf')})}}
@font-face{{font-family:HalSerif;font-style:italic;src:url({F('SourceSerif4-Italic.ttf')})}}
@font-face{{font-family:HalAmiri;src:url({F('AmiriQuran-Regular.ttf')})}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{background:#F6F1E7;color:#202522;font-family:HalSerif;display:flex;flex-direction:column;
justify-content:center;box-sizing:border-box;padding:260px 130px 420px}}
.k{{font-size:40px;letter-spacing:6px;color:#4F6B5B;text-transform:uppercase;margin-bottom:40px}}
.h{{font-size:92px;line-height:1.15;color:#23483B}}
.s{{font-size:46px;line-height:1.4;color:#4A544E;margin-top:44px}}
.m{{font-size:56px;line-height:1.45}}
.ar{{font-family:HalAmiri;font-size:84px;line-height:2;direction:rtl;text-align:center;color:#23483B}}
.tr{{font-style:italic;font-size:44px;line-height:1.5;color:#4A544E;text-align:center;margin-top:36px}}
.r{{font-size:36px;color:#4F6B5B;margin-top:48px;border-top:3px solid #C7A96B;padding-top:28px}}
.c{{text-align:center;align-items:center}}
img{{width:260px;height:260px;border-radius:58px;margin:0 auto 50px;display:block}}
.small{{font-size:32px;color:#4F6B5B;margin-top:70px;text-align:center}}
"""


def esc(t):
    return html.escape(t)


def hook(title, sub):
    return f'<div class="h">{esc(title)}</div><div class="s">{esc(sub)}</div>'


def hal(label, k):
    return (f'<div class="k">{esc(label)}</div><div class="m">{esc(meal[k])}</div>'
            f'<div class="r">{esc(ref(k))} · Meal: Elmalılı Hamdi Yazır</div>')


def arabic(k):
    x = items[k]
    return f'<div class="ar">{esc(x["arabic"])}</div><div class="tr">{esc(x["transliteration"])}</div>'


def meal_only(k):
    return f'<div class="m">{esc(meal[k])}</div><div class="r">{esc(ref(k))} · Meal: Elmalılı Hamdi Yazır</div>'


CTA = (f'<div class="c" style="text-align:center"><img src="{ICON}"><div class="h">HÂL</div>'
       '<div class="s">Bugün nasılsın?<br>Hâline uygun bir ayet, bir dakikada.</div>'
       '<div class="s" style="color:#23483B">Yakında App Store\'da</div>'
       '<div class="small">Reklamsız · Veri toplamaz · Hesap gerekmez</div></div>')

POSTS = {
    "1-bugun-nasilsin": [
        hook("Bugün nasılsın?", "Hâline göre bir ayet. Kaydır →"),
        hal("Zor bir gündeysen", "94:5"),
        hal("İçin daralıyorsa", "13:28"),
        hal("Kendini yalnız hissediyorsan", "93:3"),
        hal("Kaygılıysan", "65:3"),
        CTA,
    ],
    "2-zorlukla-kolaylik": [
        hook("Zor bir gün mü geçiriyorsun?", "Bu ayet sana. Kaydır →"),
        arabic("94:5"),
        meal_only("94:5"),
        CTA,
    ],
    "3-yakinim": [
        hook("Dua ederken kendini uzak mı hissediyorsun?", "Kaydır →"),
        arabic("2:186"),
        meal_only("2:186"),
        CTA,
    ],
}

if OUT.exists():
    shutil.rmtree(OUT)
for name, slides in POSTS.items():
    d = OUT / name
    d.mkdir(parents=True)
    for i, body in enumerate(slides, 1):
        f = TMP / f"{name}-{i}.html"
        f.write_text(f"<!doctype html><html lang=tr><meta charset=utf-8><style>{CSS}</style><body>{body}</body>", encoding="utf-8")
        png = d / f"{i}.png"
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        "--force-device-scale-factor=1", "--virtual-time-budget=5000", f"--window-size={W},{H}", f"--screenshot={png}", f.as_uri()],
                       check=True, capture_output=True, timeout=60)
shutil.copy(APP / "ios/Runner/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png", OUT / "profil-foto.png")
print("ok")
