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
.ara{background:#FFFDF7;border-radius:60px;padding:34px 50px;font-size:50px;color:#202522;
     box-shadow:0 12px 40px rgba(35,72,59,.12);margin-bottom:40px}
.ara:before{content:"⌕  ";color:#8A918C}
.gc{font-size:48px;line-height:1.9;color:#4A544E}
.gc:before{content:"↺  ";color:#C7A96B}
.tas{font-size:48px;line-height:1.35;color:#202522;padding:26px 0;border-bottom:2px solid #E4DCCB}
.tas b{display:block;font-weight:normal;font-size:34px;color:#B5533C;letter-spacing:2px;margin-bottom:8px}
.pil{width:420px;height:190px;border:10px solid #23483B;border-radius:44px;margin:0 auto;position:relative;padding:18px;
     box-sizing:border-box}
.pil:after{content:"";position:absolute;right:-40px;top:55px;width:22px;height:60px;background:#23483B;border-radius:0 12px 12px 0}
.pil i{display:block;height:100%;width:6%;background:#B5533C;border-radius:20px}
.yuzde{font-size:120px;color:#B5533C;text-align:center;margin-top:50px}
.kilit{text-align:center;color:#23483B}
.kilit .saat{font-size:220px;line-height:1}
.kilit .gun{font-size:50px;color:#4F6B5B;margin-top:10px}
.kilit .yok{font-size:42px;color:#8A918C;margin-top:160px;letter-spacing:2px}
.ani{background:#FFFDF7;border-radius:40px;overflow:hidden;box-shadow:0 12px 40px rgba(35,72,59,.12)}
.ani .foto{height:520px;background:linear-gradient(160deg,#9FB3A6,#4F6B5B 60%,#23483B)}
.ani .alt{padding:40px 50px;font-size:46px;color:#202522}
.ani .alt b{display:block;font-weight:normal;font-size:34px;color:#8A918C;letter-spacing:2px;margin-bottom:10px}
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


# 3 · Arama geçmişi
ARAMALAR = ["neden hep ben", "nasıl rahatlarım", "uyuyamıyorum ne yapmalı"]


def arama(n, c=None):
    gc = "".join(f'<div class="gc{"" if i < n else " off"}">{v.e(x)}</div>' for i, x in enumerate(ARAMALAR))
    return f'<div class="k">HÂL anları · 3</div><div class="ara">Ara</div>{gc}{cap(c)}'


# 4 · Taslaklar
TASLAKLAR = ["Aslında çok yoruldum…", "Bugün iyi değilim, sadece…", "Kimseye söyleyemedim ama"]


def taslak(n, c=None):
    t = "".join(f'<div class="tas{"" if i < n else " off"}"><b>TASLAK</b>{v.e(x)}</div>' for i, x in enumerate(TASLAKLAR))
    return f'<div class="k">HÂL anları · 4</div>{t}{cap(c)}'


# 5 · %3
def pil(c=None, yuzde=True):
    y = '<div class="yuzde">%3</div>' if yuzde else '<div class="yuzde off">%3</div>'
    return f'<div class="k">HÂL anları · 5</div><div class="pil"><i></i></div>{y}{cap(c)}'


# 6 · Bildirim yok
def kilit(c=None):
    return ('<div class="k">HÂL anları · 6</div><div class="kilit"><div class="saat">23:14</div>'
            f'<div class="gun">Pazar</div><div class="yok">Bildirim yok</div></div>{cap(c)}')


# 7 · Bir yıl önce bugün
def ani(c=None):
    return ('<div class="k">HÂL anları · 7</div><div class="ani"><div class="foto"></div>'
            '<div class="alt"><b>BİR YIL ÖNCE BUGÜN</b>"Bu da geçer mi, bilmiyorum."</div></div>' + cap(c))


BOLUMLER = {
    "21-gorduldu": [
        (chat([]), 1.8), (chat(["23:30"]), 1.3), (chat(["23:30", "00:12"]), 1.3),
        (chat(["23:30", "00:12"], "Bazen cevap gelmez."), 2.0),
        (v.hook("Ama bir kapı hep açık."), 2.2), *ayet("2:186"), (cta(), 3.5)],
    "22-gece-listesi": [
        (notlar(1), 1.4), (notlar(2), 1.1), (notlar(3), 1.1), (notlar(4), 1.6),
        (notlar(4, "Hepsini bu gece çözemezsin."), 2.2),
        (v.hook("Bir kısmını O'na bırak."), 2.2), *ayet("33:3"), (cta(), 3.5)],
    "23-arama-gecmisi": [
        (arama(0), 1.0), (arama(1), 1.2), (arama(2), 1.2), (arama(3), 1.6),
        (arama(3, "Cevabı hep başka yerde aradın."), 2.2),
        (v.hook("Bir de buradan bak."), 2.0), *ayet("2:45"), (cta(), 3.5)],
    "24-taslaklar": [
        (taslak(1), 1.4), (taslak(2), 1.3), (taslak(3), 1.6),
        (taslak(3, "Hiçbirini gönderemedin."), 2.2),
        (v.hook("O'na anlatabilirsin."), 2.0), *ayet("12:86"), (cta(), 3.5)],
    "25-yuzde-uc": [
        (pil(), 1.6), (pil("Telefonunu hemen şarja taktın."), 2.2),
        (pil("Peki ya kendin?"), 2.0),
        (v.hook("Kendine bu kadar yüklenme."), 2.2), *ayet("4:28"), (cta(), 3.5)],
    "26-bildirim-yok": [
        (kilit(), 1.8), (kilit("Bugün kimse yazmadı."), 2.2),
        (v.hook("Sen O'nu an."), 1.8), (v.hook("Sen O'nu an.", "O da seni anar."), 2.0),
        *ayet("2:152"), (cta(), 3.5)],
    "27-bir-yil-once": [
        (ani(), 2.4), (ani("Geçti."), 2.0),
        (v.hook("Bundan sonrası için de umut var."), 2.2), *ayet("93:5"), (cta(), 3.5)],
}

if __name__ == "__main__":
    v.OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        for ad in sys.argv[1:] or BOLUMLER:
            out = v.build(ad, BOLUMLER[ad], Path(d))
            print(v.sesli(out), f"{sum(x for _, x in BOLUMLER[ad]):.1f} sn")
