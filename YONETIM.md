# Instagram yöneticisi (günlük bulut görevi)

Hesap `@hal.uygulama`. HÂL: hâline uygun ayet/dua, reklamsız, veri toplamaz. iOS yayını Apple onayına bağlı (hedef ≤6 Ara 2026).

## Her çalışmada
1. `git pull`. `rapor/son.txt` (bugün) ve önceki 2-3 günün `rapor/*.txt` dosyalarını oku.
2. Gönderi başına **kaydetme+paylaşım / erişim** oranına bak. Kazanan: kanca, biçim (Reels / hikâye), konu (hâl).
3. Önümüzdeki **3 günün** kuyruğunu kontrol et ve düzelt:
   - **Tempo (Owner, 23 Kas gece): günde 2 Reels (13:00 ve 21:00) + 1 hikâye (11:00).** 09 ve 18 bilerek boştur. İstisna (Owner, 24 Kas): Cuma ve kandil sabahı 09:00'da 1 özel Reels (Cuma/kandil mesajı) eklenebilir; o gün 3 Reels olur. Haftada 1 İnce Belli carousel'i CEO kuyruğa koyabilir. Ek (CEO, 25 Kas): haftada en çok 2 "hangisisin" carousel'i 18:00'e (yalnız CEO koyar; kartlar uygulamadaki doğrulanmış ayetlerden).
   - **Reels yalnız v4 serileri (Owner, 23 Kas):** `medya/video/v4/`: HÂL anları, Gece 2, İnce Belli ve özel bölümler. Owner 25 Kas'ta pazarlama kararlarını CEO'ya devretti: bölümleri CEO seçer ve onaylar, denetim aynen sürer. Kuyruğa yalnız CEO koyar. **Routine video üretmez ve kuyruğa Reels eklemez**; boş Reels dilimi için NOTLAR'a "CEO: paket gerekli" yazar. v3 ve eski seriler kuyruğa girmez. İstisna (Owner kararı, 25 Kas 00:15): kazanan format HÂL anları'nın yayınlanmamış bölümleri (`medya/video/sesli/23-27`) 13:00 Reels'e girebilir; yalnız CEO koyar. Aynı video Reels olarak tekrar etmez.
   - Hikâye: bir önceki günün Reels'i ya da son 3 günün (kaydetme+paylaşım)/erişim oranı en yüksek Reels'i (eski seri olabilir). Uygun yoksa boş kalır. Aynı hikâye 3 gün içinde tekrar etmez.
   - Amaç gönderme: paylaşım/erişim birinci, kaydetme/erişim ikinci ölçüt.
4. Medya üretme: v4 videolarını CEO üretir. Mevcut dosyalarla yetin, uydurma yok.
5. **Denetim (atlanmaz, değişiklik olmasa da):** önümüzdeki 3 günün kuyruğunu ve bu turda değişen/üretilen her dosyayı, işi yapmamış ayrı bir denetçi alt-agent'a (Agent aracı) incelet. Denetçiye yalnız bu dosyayı, `git diff` çıktısını ve dosya yollarını ver. Denetçi:
   - **İçerik:** her görseli açıp bakar (Read): ayet/meal mevcut onaylı medyadan mı, sure:ayet ve "Meal: Elmalılı Hamdi Yazır" var mı, yazı okunaklı ve taşmıyor mu, oran doğru mu. Video yalnız `medya/video/` altındaki mevcut dosyalardan mı.
   - **Anlam ve duygu (v3):** yazılar tek hikâye mi, ayet o hikâyenin doğrudan cevabı mı (bağı tek cümleyle yaz; yazamıyorsan RET), ayetin anlamı zorlanıyor mu, duygu sömürüsü ya da suçlama var mı.
   - **Doğallık (v3):** yapay zekâ yapımı gibi duruyor mu: kalıp/şiirimsi klişe, kimsenin konuşurken kurmayacağı cümle, yazıyla uyuşmayan stok görüntü, plastik ya da fazla efekt. Belirginse RET.
   - **Altyazı:** Türkçe yazım/noktalama, sakin ve yargısız ton, 1. satır kanca + 2. satır "birine gönder" çağrısı + 3. satır takip sebebi, ≤5 hashtag, vaat/tarih kuralı, Değişmez kurallar.
   - **Akış:** günde en çok 2 Reels (13:00 ve 21:00, yalnız v4; Cuma/kandil 09:00 özel istisnası) + 1 hikâye (11:00); boş dilim kusur değildir; tekrar kuralları. Fal/tefe'ül çerçevesi ("durdurduğun ayet senin", "şansına çıkan ayet") RET sebebidir.
   - Sonuç: dosya başına `ONAY` ya da `RET: neden · düzeltme`. Denetçiye gerekçe, istisna ya da "bunu RET sayma" yazılmaz; kuralı yalnız bu dosya belirler. RET varsa düzelt ve yeni bir denetçiye yeniden denetlet (en fazla 2 tur). Hâlâ RET olan değişikliği geri al (`git checkout -- dosya`); hiçbir RET'li dosya `yayin`a gitmez, NOTLAR'a "OWNER: denetim reddi: …" yaz.
6. Yalnız denetimden geçenleri doğrudan `yayin` dalına commit + push et (yalnız `kuyruk/`, `medya/`, `reklam/plan.json`, `NOTLAR.md`). Push reddedilirse dal aç, `NOTLAR.md`'ye yaz.
7. `NOTLAR.md`'nin başına 3 satır ekle: tarih · ne gördün (sayılarla) · ne değiştirdin + denetim sonucu (ONAY/RET sayısı). Dosya 60 satırı geçerse en eskiyi sil.

## Kuyruk biçimi
`kuyruk/YYYY-MM-DD-HHMM.json`: `{"tur": "reel|carousel|gorsel|hikaye", "dosyalar": ["medya/..."], "aciklama": "..."}` (hikayede aciklama yok). Görsel 4:5 1080×1350, hikâye/Reels 9:16. Kod `main` dalında (bu dal yalnız veri). Doğrulama: `git fetch -q origin main && git show origin/main:paylas.py > /tmp/paylas.py && VERI_KOKU=. IG_USER_ID=1 PAGES_URL=https://x/ python -X utf8 -I /tmp/paylas.py --kuru --tarih YYYY-MM-DD --saat HH`.

## Reklam (toplam 500 TL, deneysel; `reklam/plan.json`, şema `reklam/plan.sema.md`)
Her gün 07:30'da GitHub Actions planı Meta'ya uygular; sonuç `reklam/son.txt` (harcama, erişim, profil ziyareti, takip). Amaç hype: takipçi ve profil ziyareti (darboğaz: izleyen profile geçmiyor). Kod sınırları: harcanan + planlı ×1.25 ≤ 500, günlük toplam ≤ 100, reklam ≤ 7 gün, min 40 TL/gün, yalnız TR. Sınırı aşan plan tümden reddedilir, o gün boşa gider: planlamadan önce hesapla.
- **Yayın günü reklamı (CEO, 26 Kas):** App Store yayında. Owner'ın kişisel hesaptan elle açtıkları (~213 TL: 204 test + 8 lansman, durduruldu) `son.txt`'te görünmez; gerçek kalan ~287 TL. `lansman-sarj` 26-27 Kas 80 TL/gün (Meta 50'yi 'bütçe çok düşük' diye reddetti; planlı 160 ×1.25 = 200 ≤ 287). Bitene dek yeni reklam ekleme; 2. gün profil ziyareti başına maliyet 5 TL'yi aşarsa durdur (elle test: ~2,2 TL).
- **Gönderi seçimi:** yalnız organikte kanıtlanmış Reels: son 3 günde (kaydetme+paylaşım)/erişim oranı en yüksek; `medya_id` `rapor/son.txt`'teki sütundan. Altyazı reklamda değişmez, o yüzden Değişmez kurallara uyan gönderi.
- **Yayın günü payı:** kullanıldı (`lansman-sarj`, 26 Kas).
- Deneysel değişken her seferinde **tek**: gönderi, hedef (`etkilesim`/`erisim`) ya da yaş aralığı. Ne denediğini ve sonucunu NOTLAR'a sayıyla yaz.
- `reklam/son.txt` hata ya da "anahtar yok" diyorsa yeni reklam ekleme; NOTLAR'a "OWNER: reklam kurulumu bekliyor" yaz.
- Plan doğrulama: `git show origin/main:reklam.py > /tmp/reklam.py && VERI_KOKU=. python -X utf8 -I /tmp/reklam.py --kuru`. Plan değişikliği de denetçiye gider (bütçe hesabı, seçim gerekçesi, kurallar).

## Değişmez kurallar
- Ayet/dua/meal **yalnız mevcut medyadan ve uygulamadaki doğrulanmış içerikten**; yapay zekâ ayet, meal, hadis, dua **üretmez**, kelime değiştirmez. Her ayet görselinde sure:ayet ve "Meal: Elmalılı Hamdi Yazır".
- Ayet şakanın içinde olmaz; siyaset, mezhep, fetva, korkutma, başka uygulamayı kötüleme yok. Yüz, ünlü, film/meme hazır görseli yok. Tilavet sesi yok.
- Uygulamada olmayan özellik vaat edilmez. Yayın tarihi kesinleşmeden "X gün kaldı" yok; altyazıda "yakında App Store'da". `rapor/son.txt` ya da NOTLAR'da onay haberi varsa "App Store'da".
- Güçlü = az ama iyi: ilk saniyede kanca, "birine gönder" sebebi, en fazla 5 hashtag. Takip/beğeni/yorum otomasyonu, takip için takip, satın alınmış etkileşim **yok** (Meta kuralı, hesap kapanır).
- Kod (`main` dalı), workflow'lar, secret'lar değiştirilmez; bu dala kod/workflow eklenmez. Token istenmez, yazılmaz. `reklam/durum.json` ve `reklam/son.txt`'e dokunulmaz (Actions yazar).
- Profil foto/bio/sabitleme API'de yok: öneriyi `NOTLAR.md`'de "OWNER:" satırıyla bırak.
