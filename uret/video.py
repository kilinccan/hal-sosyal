"""HÂL tanıtım videoları: HTML kare -> Chrome PNG -> ffmpeg geçişli MP4 (9:16, sessiz).
Kullanım: python -X utf8 -I video.py  (çıktı: medya/video/*.mp4 ve sesli/)"""
import base64, html, json, os, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("HAL_APP") or ROOT.parent / "ckappdesign" / "app")
OUT = ROOT / "medya" / "video"
SES = ROOT / "uret" / "ses" / "nps-dawnchorus.mp3"
CHROME = os.environ.get("CHROME", "C:/Program Files/Google/Chrome/Application/chrome.exe")
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
W, H, FADE = 1080, 1920, 0.6

items = {x["translation_key"]: x for x in json.load(open(APP / "assets/content/items.json", encoding="utf-8"))}
meal = json.load(open(APP / "assets/content/meal/elmalili.json", encoding="utf-8"))["texts"]
F = lambda n: "data:font/ttf;base64," + base64.b64encode((APP / "assets/fonts" / n).read_bytes()).decode()
ICON = "data:image/png;base64," + base64.b64encode(
    (APP / "ios/Runner/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png").read_bytes()).decode()

CSS = f"""
@font-face{{font-family:HalSerif;src:url({F('SourceSerif4.ttf')})}}
@font-face{{font-family:HalSerif;font-style:italic;src:url({F('SourceSerif4-Italic.ttf')})}}
@font-face{{font-family:HalAmiri;src:url({F('AmiriQuran-Regular.ttf')})}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden}}
body{{background:radial-gradient(circle at 50% 35%,#FBF8F1,#EFE8D8);color:#202522;font-family:HalSerif;
display:flex;flex-direction:column;justify-content:center;box-sizing:border-box;padding:260px 130px 440px}}
.k{{font-size:40px;letter-spacing:6px;color:#4F6B5B;text-transform:uppercase;margin-bottom:40px}}
.h{{font-size:96px;line-height:1.15;color:#23483B}}
.s{{font-size:48px;line-height:1.4;color:#4A544E;margin-top:44px}}
.m{{font-size:56px;line-height:1.45}}
.ar{{font-family:HalAmiri;font-size:84px;line-height:2;direction:rtl;text-align:center;color:#23483B}}
.tr{{font-style:italic;font-size:44px;line-height:1.5;color:#4A544E;text-align:center;margin-top:36px}}
.r{{font-size:36px;color:#4F6B5B;margin-top:48px;border-top:3px solid #C7A96B;padding-top:28px}}
.hid{{visibility:hidden}}
.c{{text-align:center}}
img{{width:260px;height:260px;border-radius:58px;margin:0 auto 50px;display:block}}
.small{{font-size:32px;color:#4F6B5B;margin-top:70px}}
.wm{{position:fixed;top:120px;left:0;right:0;text-align:center;font-size:34px;letter-spacing:8px;color:#4F6B5B}}
"""
e = html.escape


def ref(k):
    x = items[k]
    return f"{x['surah_name']} {x['surah']}:{x['ayah']}" + (f"-{x['ayah_end']}" if x.get("ayah_end") else "")


def secs(text):  # okuma süresi: ~18 harf/sn, 2.5-7 sn
    return max(2.5, min(7.0, len(text) / 18))


def hook(t, s=None):
    return f'<div class="h">{e(t)}</div>' + (f'<div class="s">{e(s)}</div>' if s else "")


def hal(label, k, show):
    v = "" if show else " hid"
    return (f'<div class="k">{e(label)}</div><div class="m{v}">{e(meal[k])}</div>'
            f'<div class="r{v}">{e(ref(k))} · Meal: Elmalılı Hamdi Yazır</div>')


def ar(k, tr):
    x = items[k]
    return f'<div class="ar">{e(x["arabic"])}</div><div class="tr{"" if tr else " hid"}">{e(x["transliteration"])}</div>'


def mealf(k):
    return f'<div class="m">{e(meal[k])}</div><div class="r">{e(ref(k))} · Meal: Elmalılı Hamdi Yazır</div>'


CTA = (f'<div class="c"><img src="{ICON}"><div class="h">HÂL</div>'
       '<div class="s">Bugün nasılsın?<br>Hâline uygun bir ayet, bir dakikada.</div>'
       '<div class="s" style="color:#23483B">Yakında App Store\'da</div>'
       '<div class="small">Reklamsız · Veri toplamaz · Hesap gerekmez</div></div>')


def hal_seq(label, k):
    return [(hal(label, k, False), 1.2), (hal(label, k, True), secs(meal[k]))]


def ayet_seq(k):
    return [(ar(k, False), 2.0), (ar(k, True), 3.0), (mealf(k), secs(meal[k]))]


VIDEOS = {
    "1-bugun-nasilsin": [(hook("Bugün nasılsın?"), 1.3), (hook("Bugün nasılsın?", "Hâline göre bir ayet."), 1.8),
                         *hal_seq("Zor bir gündeysen", "94:5"), *hal_seq("İçin daralıyorsa", "13:28"),
                         *hal_seq("Kendini yalnız hissediyorsan", "93:3"), *hal_seq("Kaygılıysan", "65:3"), (CTA, 3.5)],
    "2-zorlukla-kolaylik": [(hook("Zor bir gün mü geçiriyorsun?"), 2.3), *ayet_seq("94:5"), (CTA, 3.5)],
    "3-yakinim": [(hook("Dua ederken kendini uzak mı hissediyorsun?"), 2.8), *ayet_seq("2:186"), (CTA, 3.5)],
    "4-kalpler": [(hook("İçin daralıyorsa"), 2.0), *ayet_seq("13:28"), (CTA, 3.5)],
    "5-yalniz-degilsin": [(hook("Kendini yalnız mı hissediyorsun?"), 2.3), *ayet_seq("93:3"), (CTA, 3.5)],
    "6-korkma": [(hook("Bir şeyden korkuyor musun?"), 2.3), *ayet_seq("20:46"), (CTA, 3.5)],
    "7-umit": [(hook("Kendini affedemiyor musun?"), 2.3), *ayet_seq("39:53"), (CTA, 3.5)],
    "8-yakin": [(hook("Kimse seni anlamıyor gibi mi?"), 2.3), *ayet_seq("50:16"), (CTA, 3.5)],
    "9-say": [(hook("Hiç saymaya çalıştın mı?"), 2.3), *ayet_seq("16:18"), (CTA, 3.5)],
    "10-dinlen": [(hook("Biraz dinlenmeye ihtiyacın mı var?"), 2.5), *ayet_seq("28:73"), (CTA, 3.5)],
    "11-sabir": [(hook("Sabretmekte zorlanıyor musun?"), 2.3), *ayet_seq("2:153"), (CTA, 3.5)],
    "12-mahzun-olma": [(hook("Gücün mü tükeniyor?"), 2.0), *ayet_seq("3:139"), (CTA, 3.5)],
    "13-sikayet": [(hook("Derdini kimseye anlatamıyor musun?"), 2.5), *ayet_seq("12:86"), (CTA, 3.5)],
    "14-umit": [(hook("Umudun azaldı mı?"), 2.0), *ayet_seq("42:28"), (CTA, 3.5)],
    "15-yeter": [(hook("Her şeyi tek başına taşımaya mı çalışıyorsun?"), 2.8), *ayet_seq("33:3"), (CTA, 3.5)],
    "16-sabri-cemil": [(hook("Biraz daha sabra mı ihtiyacın var?"), 2.5), *ayet_seq("70:5"), (CTA, 3.5)],
    "17-sonu-hayirli": [(hook("Yarın için endişeli misin?"), 2.3), *ayet_seq("93:4"), (CTA, 3.5)],
    "18-zayif": [(hook("Kendini zayıf mı hissediyorsun?"), 2.3), *ayet_seq("4:28"), (CTA, 3.5)],
    "19-gogsume": [(hook("İçin sıkışıyorsa, bu duayı oku."), 2.5), *ayet_seq("20:25"), (CTA, 3.5)],
    "20-kayip": [(hook("Bir kayıp mı yaşadın?"), 2.0), *ayet_seq("2:156"), (CTA, 3.5)],
}


def render(body, png, tmp):
    f = tmp / (png.stem + ".html")
    f.write_text(f'<!doctype html><html lang=tr><meta charset=utf-8><style>{CSS}</style>'
                 f'<body><div class="wm">HÂL</div>{body}</body>', encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--virtual-time-budget=5000", f"--window-size={W},{H}", f"--screenshot={png}", f.as_uri()],
                   check=True, capture_output=True, timeout=60)


def build(name, seq, tmp):
    pngs = []
    for i, (body, _) in enumerate(seq):
        p = tmp / f"{name}-{i:02d}.png"
        render(body, p, tmp)
        pngs.append(p)
    args, filt, last, t = [FFMPEG, "-y", "-loglevel", "error"], [], "[0:v]", 0.0
    for p, (_, d) in zip(pngs, seq):
        args += ["-loop", "1", "-framerate", "30", "-t", f"{d + FADE:.2f}", "-i", str(p)]
    for i in range(1, len(seq)):
        t += seq[i - 1][1]
        filt.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={t:.2f}[v{i}]")
        last = f"[v{i}]"
    filt.append(f"{last}fade=t=in:st=0:d=0.5,format=yuv420p[out]")
    out = OUT / f"{name}.mp4"
    args += ["-filter_complex", ";".join(filt), "-map", "[out]", "-r", "30", "-c:v", "libx264",
             "-preset", "slow", "-crf", "18", "-movflags", "+faststart", str(out)]
    subprocess.run(args, check=True)
    return out


def sesli(src):
    """Sessiz MP4'e şafak kuşları kaydını (NPS, kamu malı: uret/ses/KAYNAK.txt) ekler -> video/sesli/."""
    dur = float(subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
        check=True, capture_output=True, text=True).stdout)
    dst = OUT / "sesli" / src.name
    dst.parent.mkdir(exist_ok=True)
    af = ("highpass=f=900,highpass=f=900,afftdn=nr=10,loudnorm=I=-27:TP=-6,"
          f"afade=t=in:st=0:d=1.5,afade=t=out:st={dur - 2:.2f}:d=2")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src), "-stream_loop", "-1", "-i", str(SES),
                    "-map", "0:v", "-map", "1:a", "-t", f"{dur:.2f}", "-c:v", "copy", "-af", af,
                    "-ar", "48000", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)], check=True)
    return dst


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        for n, s in VIDEOS.items():
            out = build(n, s, Path(d))
            print(out, f"{sum(x for _, x in s):.0f} sn")
            print(sesli(out))
