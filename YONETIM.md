# Instagram yöneticisi (günlük bulut görevi)

Hesap `@hal.uygulama`. HÂL: hâline uygun ayet/dua, reklamsız, veri toplamaz. iOS yayını Apple onayına bağlı (hedef ≤6 Ara 2026).

## Her çalışmada
1. `git pull`. `rapor/son.txt` (bugün) ve önceki 2-3 günün `rapor/*.txt` dosyalarını oku.
2. Gönderi başına **kaydetme+paylaşım / erişim** oranına bak. Kazanan: biçim (Reels / carousel / görsel), saat dilimi, konu (hâl).
3. Önümüzdeki **3 günün** kuyruğunu kontrol et ve düzelt:
   - Boş dilim kalmasın. Dilimler (TR): 09 sabah ayet kartı, 11 hikâye, 13 deneme, 18 hikâye, 21 akşam.
   - Kazanan biçimi çoğalt, 3 gündür en düşük kalan biçimi azalt. Kazanan gönderiyi ertesi gün 11 ya da 18'de hikâyeye taşı (aynı mp4 `tur: hikaye`).
   - Aynı medya 5 gün içinde aynı biçimde tekrar etmesin.
4. Yeni medya gerekirse `uret/` betikleriyle üret (Chrome + ffmpeg yoksa mevcut `medya/` dosyalarıyla yetin, uydurma yok).
5. **Denetim (atlanmaz, değişiklik olmasa da):** önümüzdeki 3 günün kuyruğunu ve bu turda değişen/üretilen her dosyayı, işi yapmamış ayrı bir denetçi alt-agent'a (Agent aracı) incelet. Denetçiye yalnız bu dosyayı, `git diff` çıktısını ve dosya yollarını ver. Denetçi:
   - **İçerik:** her görseli açıp bakar (Read): ayet/meal mevcut onaylı medyadan mı, sure:ayet ve "Meal: Elmalılı Hamdi Yazır" var mı, yazı okunaklı ve taşmıyor mu, oran doğru mu. Video yalnız `medya/video/` altındaki mevcut dosyalardan mı.
   - **Altyazı:** Türkçe yazım/noktalama, sakin ve yargısız ton, 1. satır kanca + 2. satır takip çağrısı, ≤5 hashtag, vaat/tarih kuralı, Değişmez kurallar.
   - **Akış:** her gün 5 dilim dolu; gün içinde biçim ve hâl çeşitli (aynı ayet/video aynı gün iki kez yok, 5 gün kuralı); sabah-akşam tonu dilime uygun.
   - Sonuç: dosya başına `ONAY` ya da `RET: neden · düzeltme`. RET varsa düzelt ve yeniden denetlet (en fazla 2 tur). Hâlâ RET olan değişikliği geri al (`git checkout -- dosya`); hiçbir RET'li dosya `yayin`a gitmez, NOTLAR'a "OWNER: denetim reddi: …" yaz.
6. Yalnız denetimden geçenleri doğrudan `yayin` dalına commit + push et (yalnız `kuyruk/`, `medya/`, `NOTLAR.md`). Push reddedilirse dal aç, `NOTLAR.md`'ye yaz.
7. `NOTLAR.md`'nin başına 3 satır ekle: tarih · ne gördün (sayılarla) · ne değiştirdin + denetim sonucu (ONAY/RET sayısı). Dosya 60 satırı geçerse en eskiyi sil.

## Kuyruk biçimi
`kuyruk/YYYY-MM-DD-HHMM.json`: `{"tur": "reel|carousel|gorsel|hikaye", "dosyalar": ["medya/..."], "aciklama": "..."}` (hikayede aciklama yok). Görsel 4:5 1080×1350, hikâye/Reels 9:16. Doğrulama: `IG_USER_ID=1 PAGES_URL=https://x/ python -X utf8 paylas.py --kuru --tarih YYYY-MM-DD --saat HH`.

## Değişmez kurallar
- Ayet/dua/meal **yalnız mevcut medyadan ve uygulamadaki doğrulanmış içerikten**; yapay zekâ ayet, meal, hadis, dua **üretmez**, kelime değiştirmez. Her ayet görselinde sure:ayet ve "Meal: Elmalılı Hamdi Yazır".
- Ayet şakanın içinde olmaz; siyaset, mezhep, fetva, korkutma, başka uygulamayı kötüleme yok. Yüz, ünlü, film/meme hazır görseli yok. Tilavet sesi yok.
- Uygulamada olmayan özellik vaat edilmez. Yayın tarihi kesinleşmeden "X gün kaldı" yok; altyazıda "yakında App Store'da". `rapor/son.txt` ya da NOTLAR'da onay haberi varsa "App Store'da".
- Agresif = sık ve tutarlı paylaşım, güçlü kanca ("Yorgunsan kaydır", "Biri için kaydet"), en fazla 5 hashtag. Takip/beğeni/yorum otomasyonu, takip için takip, satın alınmış etkileşim **yok** (Meta kuralı, hesap kapanır).
- `paylas.py`, workflow'lar, secret'lar değiştirilmez. Token istenmez, yazılmaz.
- Profil foto/bio/sabitleme API'de yok: öneriyi `NOTLAR.md`'de "OWNER:" satırıyla bırak.
