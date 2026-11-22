# Instagram yöneticisi (günlük bulut görevi)

Hesap `@hal.uygulama`. HÂL: hâline uygun ayet/dua, reklamsız, veri toplamaz. iOS yayını Apple onayına bağlı (hedef ≤6 Ara 2026).

## Her çalışmada
1. `git pull`. `rapor/son.txt` (bugün) ve önceki 2-3 günün `rapor/*.txt` dosyalarını oku.
2. Gönderi başına **kaydetme+paylaşım / erişim** oranına bak. Kazanan: biçim (Reels / carousel / görsel), saat dilimi, konu (hâl).
3. Önümüzdeki **3 günün** kuyruğunu kontrol et ve düzelt:
   - Boş dilim kalmasın. Dilimler (TR): 09 sabah ayet kartı, 11 hikâye, 13 Reels, 18 Reels, 21 akşam.
   - **Strateji (Owner, 22 Kas): Reels öncelikli** (en çok etkileşim onlarda). Yeni Reels "HÂL anları" serisi: tanıdık bir an (POV: mesaj, gece notu…) → tek cümle köprü → ayet → kapanış; bölüm numaralı, üretim `uret/anlar.py`. Aynı videoyu yeniden kuyruğa koyma; yeni bölüm üret. Üretemiyorsan dilimi carousel/görselle doldur, eski Reels'i tekrarlama, NOTLAR'a "OWNER: yeni bölüm gerekli" yaz.
   - Kazanan biçimi çoğalt, 3 gündür en düşük kalan biçimi azalt. Kazanan gönderiyi ertesi gün 11 ya da 18'de hikâyeye taşı (aynı mp4 `tur: hikaye`).
   - Aynı medya 5 gün içinde aynı biçimde tekrar etmesin (hikâyede 3 gün; hikâye 24 saatte kaybolur).
4. Yeni medya gerekirse `uret/` betikleriyle üret (Chrome + ffmpeg yoksa mevcut `medya/` dosyalarıyla yetin, uydurma yok).
5. **Denetim (atlanmaz, değişiklik olmasa da):** önümüzdeki 3 günün kuyruğunu ve bu turda değişen/üretilen her dosyayı, işi yapmamış ayrı bir denetçi alt-agent'a (Agent aracı) incelet. Denetçiye yalnız bu dosyayı, `git diff` çıktısını ve dosya yollarını ver. Denetçi:
   - **İçerik:** her görseli açıp bakar (Read): ayet/meal mevcut onaylı medyadan mı, sure:ayet ve "Meal: Elmalılı Hamdi Yazır" var mı, yazı okunaklı ve taşmıyor mu, oran doğru mu. Video yalnız `medya/video/` altındaki mevcut dosyalardan mı.
   - **Altyazı:** Türkçe yazım/noktalama, sakin ve yargısız ton, 1. satır kanca + 2. satır takip çağrısı, ≤5 hashtag, vaat/tarih kuralı, Değişmez kurallar.
   - **Akış:** her gün 5 dilim dolu; gün içinde biçim ve hâl çeşitli (aynı ayet/video aynı gün iki kez yok, 5 gün kuralı); sabah-akşam tonu dilime uygun.
   - Sonuç: dosya başına `ONAY` ya da `RET: neden · düzeltme`. Denetçiye gerekçe, istisna ya da "bunu RET sayma" yazılmaz; kuralı yalnız bu dosya belirler. RET varsa düzelt ve yeni bir denetçiye yeniden denetlet (en fazla 2 tur). Hâlâ RET olan değişikliği geri al (`git checkout -- dosya`); hiçbir RET'li dosya `yayin`a gitmez, NOTLAR'a "OWNER: denetim reddi: …" yaz.
6. Yalnız denetimden geçenleri doğrudan `yayin` dalına commit + push et (yalnız `kuyruk/`, `medya/`, `reklam/plan.json`, `NOTLAR.md`). Push reddedilirse dal aç, `NOTLAR.md`'ye yaz.
7. `NOTLAR.md`'nin başına 3 satır ekle: tarih · ne gördün (sayılarla) · ne değiştirdin + denetim sonucu (ONAY/RET sayısı). Dosya 60 satırı geçerse en eskiyi sil.

## Kuyruk biçimi
`kuyruk/YYYY-MM-DD-HHMM.json`: `{"tur": "reel|carousel|gorsel|hikaye", "dosyalar": ["medya/..."], "aciklama": "..."}` (hikayede aciklama yok). Görsel 4:5 1080×1350, hikâye/Reels 9:16. Kod `main` dalında (bu dal yalnız veri). Doğrulama: `git fetch -q origin main && git show origin/main:paylas.py > /tmp/paylas.py && VERI_KOKU=. IG_USER_ID=1 PAGES_URL=https://x/ python -X utf8 -I /tmp/paylas.py --kuru --tarih YYYY-MM-DD --saat HH`.

## Reklam (toplam 500 TL, deneysel; `reklam/plan.json`, şema `reklam/plan.sema.md`)
Her gün 07:30'da GitHub Actions planı Meta'ya uygular; sonuç `reklam/son.txt` (harcama, erişim, profil ziyareti, takip). Amaç hype: takipçi ve profil ziyareti (darboğaz: izleyen profile geçmiyor). Kod sınırları: harcanan + planlı ×1.25 ≤ 500, günlük toplam ≤ 100, reklam ≤ 7 gün, min 40 TL/gün, yalnız TR. Sınırı aşan plan tümden reddedilir, o gün boşa gider: planlamadan önce hesapla.
- **Gönderi seçimi:** yalnız organikte kanıtlanmış Reels: son 3 günde (kaydetme+paylaşım)/erişim oranı en yüksek; `medya_id` `rapor/son.txt`'teki sütundan. Altyazı reklamda değişmez, o yüzden Değişmez kurallara uyan gönderi.
- **Faz 1, test (2 gün):** iki reklam paralel, 40 TL/gün, `hedef: profil_ziyareti`: A = en iyi Reels, B = ikinci en iyi (tercihen farklı hâl/kanca). Ölçüt: profil ziyareti başına maliyet, sonra yeni takipçi.
- **Faz 2, ölçek:** kazanan 3-4 gün 50-60 TL/gün; kaybeden `durdur`. 1 gün sonunda profil ziyareti başına maliyet 5 TL'yi aşan ve takip getirmeyen reklam `durdur`.
- **Yayın günü payı:** ~150 TL harcanmadan tutulur; App Store onay haberi (NOTLAR/rapor) gelince yayın günü en iyi Reels'e 3 gün.
- Deneysel değişken her seferinde **tek**: gönderi, hedef (`etkilesim`/`erisim`) ya da yaş aralığı. Ne denediğini ve sonucunu NOTLAR'a sayıyla yaz.
- `reklam/son.txt` hata ya da "anahtar yok" diyorsa yeni reklam ekleme; NOTLAR'a "OWNER: reklam kurulumu bekliyor" yaz.
- Plan doğrulama: `git show origin/main:reklam.py > /tmp/reklam.py && VERI_KOKU=. python -X utf8 -I /tmp/reklam.py --kuru`. Plan değişikliği de denetçiye gider (bütçe hesabı, seçim gerekçesi, kurallar).

## Değişmez kurallar
- Ayet/dua/meal **yalnız mevcut medyadan ve uygulamadaki doğrulanmış içerikten**; yapay zekâ ayet, meal, hadis, dua **üretmez**, kelime değiştirmez. Her ayet görselinde sure:ayet ve "Meal: Elmalılı Hamdi Yazır".
- Ayet şakanın içinde olmaz; siyaset, mezhep, fetva, korkutma, başka uygulamayı kötüleme yok. Yüz, ünlü, film/meme hazır görseli yok. Tilavet sesi yok.
- Uygulamada olmayan özellik vaat edilmez. Yayın tarihi kesinleşmeden "X gün kaldı" yok; altyazıda "yakında App Store'da". `rapor/son.txt` ya da NOTLAR'da onay haberi varsa "App Store'da".
- Agresif = sık ve tutarlı paylaşım, güçlü kanca ("Yorgunsan kaydır", "Biri için kaydet"), en fazla 5 hashtag. Takip/beğeni/yorum otomasyonu, takip için takip, satın alınmış etkileşim **yok** (Meta kuralı, hesap kapanır).
- Kod (`main` dalı), workflow'lar, secret'lar değiştirilmez; bu dala kod/workflow eklenmez. Token istenmez, yazılmaz. `reklam/durum.json` ve `reklam/son.txt`'e dokunulmaz (Actions yazar).
- Profil foto/bio/sabitleme API'de yok: öneriyi `NOTLAR.md`'de "OWNER:" satırıyla bırak.
