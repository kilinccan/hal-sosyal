"""'HÂL anları' POV serisi. video.py'nin render/build/sesli'sini kullanır.
Kullanım: python -X utf8 -I anlar.py [bölüm-adı ...]  (çıktı: medya/video/ ve sesli/; HAL_APP, CHROME video.py'deki gibi)"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video as v

v.CSS += """
.chat{display:flex;flex-direction:column;gap:26px}
.b{align-self:flex-end;max-width:720px;background:#23483B;color:#FBF8F1;font-size:52px;line-height:1.35;
   padding:34px 44px;border-radius:48px 48px 12px 48px}
.meta{align-self:flex-end;font-size:34px;color:#4F6B5B}
.t{align-self:center;font-size:34px;color:#8A918C;letter-spacing:2px;margin-top:40px}
.cap{font-size:76px;line-height:1.2;color:#23483B;margin-top:110px;min-height:184px}
.off{visibility:hidden}
.note{background:#FFFDF7;border-radius:40px;padding:56px 60px;box-shadow:0 12px 40px rgba(35,72,59,.12)}
.nt{font-size:40px;color:#8A918C;letter-spacing:2px}
.nh{font-size:64px;color:#23483B;margin:10px 0 30px}
.li{font-size:54px;line-height:1.7;color:#202522}
.li:before{content:"○  ";color:#C7A96B}
"""


def ayet(k):
    ref = f'<div class="r c">{v.e(v.ref(k))} · Meal: Elmalılı Hamdi Yazır</div>'
    return [(v.ar(k, False) + ref, 2.0), (v.ar(k, True) + ref, 3.0), (v.mealf(k), v.secs(v.meal[k]))]


def cta():
    return (f'<div class="c"><img src="{v.ICON}"><div class="h">HÂL</div>'
            '<div class="s">Sırada yeni bir an var.</div>'
            '<div class="s" style="color:#23483B">Seriyi kaçırmamak için takip et.</div>'
            '<div class="small">Yakında App Store\'da · Reklamsız · Veri toplamaz</div></div>')


def cap(t):
    return f'<div class="cap">{v.e(t)}</div>' if t else '<div class="cap off">.</div>'


# 1 · Görüldü
def chat(saatler, c=None):
    t = "".join(f'<div class="t{"" if s in saatler else " off"}">{s}</div>' for s in ("23:30", "00:12"))
    return ('<div class="k">HÂL anları · 1</div><div class="chat">'
            '<div class="b">Müsait misin? Biraz konuşabilir miyiz?</div>'
            f'<div class="meta">22:47 · Görüldü</div>{t}</div>{cap(c)}')


# 2 · Gece listesi
LISTE = ["Faturayı öde", "O konuşmayı yap", "Sonuç gelecek", "Ya olmazsa?"]


def notlar(n, c=None):
    li = "".join(f'<div class="li{"" if i < n else " off"}">{v.e(x)}</div>' for i, x in enumerate(LISTE))
    return (f'<div class="k">HÂL anları · 2</div><div class="note"><div class="nt">01:47</div>'
            f'<div class="nh">Yarın</div>{li}</div>{cap(c)}')


BOLUMLER = {
    "21-gorduldu": [
        (chat([]), 1.8), (chat(["23:30"]), 1.3), (chat(["23:30", "00:12"]), 1.3),
        (chat(["23:30", "00:12"], "Bazen cevap gelmez."), 2.0),
        (v.hook("Ama bir kapı hep açık."), 2.2), *ayet("2:186"), (cta(), 3.5)],
    "22-gece-listesi": [
        (notlar(1), 1.4), (notlar(2), 1.1), (notlar(3), 1.1), (notlar(4), 1.6),
        (notlar(4, "Hepsini bu gece çözemezsin."), 2.2),
        (v.hook("Bir kısmını O'na bırak."), 2.2), *ayet("33:3"), (cta(), 3.5)],
}

if __name__ == "__main__":
    v.OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        for ad in sys.argv[1:] or BOLUMLER:
            out = v.build(ad, BOLUMLER[ad], Path(d))
            print(v.sesli(out), f"{sum(x for _, x in BOLUMLER[ad]):.1f} sn")
