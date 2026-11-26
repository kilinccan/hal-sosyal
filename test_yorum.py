"""Ağsız birim testleri: python -X utf8 -m unittest test_yorum"""
import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yorum

VERI = json.loads(yorum.VERI.read_text(encoding="utf-8"))
SIMDI = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
STRINGS = Path("C:/Users/lastp/Documents/ckapp-wt/app/lib/core/strings.dart")
BIZ = {"username": yorum.BIZIM, "timestamp": "2026-11-26T11:00:00+0000"}


def y(text, username="u", id="1", ts="2026-11-26T10:00:00+0000", **kw):
    return {"id": id, "text": text, "username": username, "timestamp": ts, **kw}


def cevapli(**kw):
    return y("yorgun", replies={"data": [BIZ]}, **kw)


def ad(text):
    s = yorum.cevap_metni(y(text), VERI)
    return s and s[0]


def calistir(yorumlar, baslangic=None):
    return yorum.calistir([(baslangic, yorumlar)], VERI, None, SIMDI, True)[0]


class Esleme(unittest.TestCase):
    def test_anahtar_kelimeler(self):
        for metin, beklenen in [("Yorgunum", "yorgun"), ("KAYGILI", "kaygi"), ("endişeli", "kaygi"),
                                ("Kırgın", "uzgun"), ("Şükür", "sukur"), ("iyiyim", "sukur"),
                                ("yalnızım", "yalniz"), ("sabır", "sabir"), ("umut", "umut"),
                                ("korkuyorum", "kaygi"), ("öfkeliyim", "ofke")]:
            with self.subTest(metin):
                self.assertEqual(ad(metin), beklenen)

    def test_eslesme_yoksa_cevap_yok(self):
        self.assertIsNone(ad("hmm"))

    def test_olumsuzlama_cevap_yok(self):
        for metin in ["iyi değilim", "mutlu değilim", "yorgun değilim", "hiç kaygılı değil"]:
            with self.subTest(metin):
                self.assertIsNone(ad(metin))

    def test_cevap_bicimi_ve_sinir(self):
        _, m = yorum.cevap_metni(y("yorgun", username="ayse"), VERI)
        self.assertTrue(m.startswith("@ayse ") and "«" in m and m.endswith("🤍"))
        for grup, liste in VERI["ayetler"].items():
            self.assertGreaterEqual(len(liste), 3, grup)
            for i, a in enumerate(liste):
                self.assertLessEqual(len(a["meal"]), 200, grup)
                m = yorum.cevap_metni(y("yorgun", username="x" * 30, id=str(i)), VERI)[1]
                self.assertLessEqual(len(m), 300)

    def test_her_anahtar_grubunun_ayeti_var_genel_yok(self):
        for grup, _ in yorum.ANAHTAR:
            self.assertIn(grup, VERI["ayetler"])
        self.assertNotIn("genel", VERI["ayetler"])

    def test_giris_cesitliligi_deterministik(self):
        girisler = {yorum.cevap_metni(y("yorgun", id=str(i)), VERI)[1].split("«")[0] for i in range(60)}
        self.assertGreaterEqual(len(girisler), 3)
        self.assertEqual(yorum.cevap_metni(y("yorgun", id="9"), VERI), yorum.cevap_metni(y("yorgun", id="9"), VERI))

    def test_isaretlenen_mealler_cikarildi(self):
        tum = {(a["sure"], a["ayet"]) for l in VERI["ayetler"].values() for a in l}
        for sure, ayet in [("Bakara", 45), ("Âl-i İmrân", 139), ("Nisâ", 110), ("Nahl", 127), ("A'râf", 56),
                           ("Lokmân", 17), ("Zümer", 66), ("Yûnus", 62), ("Ahkāf", 13)]:
            self.assertNotIn((sure, ayet), tum)


class Kriz(unittest.TestCase):
    METINLER = ["ölmek istiyorum", "Kendime zarar vermek istiyorum", "yaşamak istemiyorum", "intihar",
                "ölmek en iyisi", "umutsuzum", "dayanamıyorum", "hayatım bitti", "bittim", "yok olmak istiyorum",
                "bileğimi keseceğim", "kendimi öldüreceğim", "suicide", "keşke ölsem"]

    def test_kriz_ayetsiz_destek_ve_kullanicisiz(self):
        for metin in self.METINLER:
            with self.subTest(metin):
                ad_, m = yorum.cevap_metni(y(metin, username="ayse"), VERI)
                self.assertEqual(ad_, "kriz")
                self.assertEqual(m, yorum.DESTEK)
                self.assertNotIn("@", m)
                self.assertNotIn("«", m)
                self.assertIn("112", m)
                self.assertLessEqual(len(m), 300)

    def test_kriz_ihtiyac_ve_filtrelerden_once(self):
        for metin in ["yorgunum ölmek istiyorum", "ölmek istiyorum https://x.co @biri #a",
                      "çok zor günler geçiriyorum artık kendime zarar vermek istiyorum", "salak hayatım bitti"]:
            with self.subTest(metin):
                self.assertEqual(ad(metin), "kriz")

    def test_ayni_kisi_normal_sonra_kriz(self):
        s = calistir([y("yorgun", id="1", ts="2026-11-26T09:00:00+0000"),
                      y("ölmek istiyorum", id="2", ts="2026-11-26T10:00:00+0000")])
        self.assertEqual((s["ihtiyac:yorgun"], s["ihtiyac:kriz"]), (1, 1))

    def test_kriz_gunluk_kisi_ve_kosu_sinirlarindan_muaf(self):
        onceki = y("yorgun", id="0", replies={"data": [BIZ]})
        krizler = [y("intihar https://x.co", id=str(i)) for i in range(1, 16)]
        s = calistir([onceki] + krizler)
        self.assertEqual(s["ihtiyac:kriz"], 15)

    def test_kriz_gun_siniri_dolu_iken_de_gider(self):
        dolu = [y("yorgun", username=f"d{i}", id=f"d{i}", replies={"data": [BIZ]}) for i in range(yorum.EN_COK_GUN)]
        s = calistir(dolu + [y("yorgun", id="n"), y("ölmek istiyorum", id="k")])
        self.assertEqual((s["ihtiyac:kriz"], s["sinir"], s["cevap"]), (1, 1, 1))

    def test_kriz_once_islenir(self):
        yorumlar = [y("umut", username=f"p{i}", id=str(i)) for i in range(15)]
        yorumlar.append(y("intihar", id="k", ts="2026-11-26T11:59:00+0000"))
        self.assertEqual(calistir(yorumlar)["ihtiyac:kriz"], 1)

    def test_destek_metni_strings_dart_ile_ayni(self):
        if not STRINGS.exists():
            self.skipTest("strings.dart yok")
        kaynak = STRINGS.read_text(encoding="utf-8")

        def sabit(ad_):
            g = re.search(rf"static const {ad_} =\s*((?:'[^']*'\s*)+);", kaynak)
            return "".join(re.findall(r"'([^']*)'", g[1]))

        beklenen = f"{sabit('crisisBody')} {sabit('crisisEmergency')} · {sabit('crisisSocial')} 🤍"
        self.assertEqual(yorum.DESTEK, beklenen)


class Atlama(unittest.TestCase):
    def test_uzun_linkli_hakaret_atlanir(self):
        for metin in ["a" * 61, "bak https://x.co", "www.site.com", "@baskasi yorgun", "salak yorgun",
                      "amk yorgun", "orospu çocuğu"]:
            with self.subTest(metin):
                self.assertIsNone(yorum.cevap_metni(y(metin), VERI))

    def test_60_karakter_serbest(self):
        self.assertIsNotNone(yorum.cevap_metni(y("yorgun " + "a" * 53), VERI))

    def test_zaten_cevaplanmis_atlanir(self):
        a = yorum.adaylar([cevapli(), y("kaygı", username="v", id="2")], SIMDI, None)
        self.assertEqual([x["id"] for x in a], ["2"])

    def test_ayni_kisiye_gunde_tek_cevap(self):
        s = calistir([y("yorgun", id="1"), y("kaygı", id="2")])
        self.assertEqual(s["cevap"], 1)
        s = calistir([cevapli(id="1"), y("kaygı", id="2")])
        self.assertEqual(s["cevap"], 0)

    def test_eski_kendi_ve_baslangic_oncesi_atlanir(self):
        self.assertEqual(yorum.adaylar([y("yorgun", ts="2026-11-01T10:00:00+0000"),
                                        y("yorgun", username=yorum.BIZIM, id="3")], SIMDI, None), [])
        bas = datetime(2026, 11, 26, 9, 30, tzinfo=timezone.utc)
        a = yorum.adaylar([y("yorgun", id="1", ts="2026-11-26T09:00:00+0000"),
                           y("yorgun", id="2", ts="2026-11-26T10:00:00+0000")], SIMDI, bas)
        self.assertEqual([x["id"] for x in a], ["2"])

    def test_replies_username_yoksa_durur(self):
        with self.assertRaises(yorum.Durdur):
            yorum.adaylar([y("yorgun", replies={"data": [{"id": "1"}]})], SIMDI, None)


class Sinirlar(unittest.TestCase):
    def test_kosu_siniri(self):
        s = calistir([y("yorgun", username=f"k{i}", id=str(i)) for i in range(40)])
        self.assertEqual((s["cevap"], s["sinir"]), (yorum.EN_COK_KOSU, 30))

    def test_gun_siniri_tum_medyalar(self):
        dolu = [y("yorgun", username=f"d{i}", id=f"d{i}", replies={"data": [BIZ]}) for i in range(yorum.EN_COK_GUN - 3)]
        yeni = [y("yorgun", username=f"k{i}", id=f"k{i}") for i in range(10)]
        s = yorum.calistir([(None, dolu), (None, yeni)], VERI, None, SIMDI, True)[0]
        self.assertEqual(s["cevap"], 3)


class Hatalar(unittest.TestCase):
    def test_kisalt_yalniz_kod(self):
        ex = yorum.Hata('400 123/replies: {"error": {"message": "ayse yorgun", "code": 190}}')
        self.assertEqual(yorum.kisalt(ex), "HTTP 400, kod 190")
        self.assertEqual(yorum.kisalt(yorum.Hata("123/replies: ayse")), "ağ hatası")

    def test_hesap_uyusmazsa_cevap_yok(self):
        with mock.patch.object(yorum, "HESAP", "1"), mock.patch.object(yorum, "istek", return_value={"username": "baskasi"}):
            with self.assertRaises(yorum.Durdur):
                yorum.hesabi_dogrula("t")
        with mock.patch.object(yorum, "HESAP", "1"), mock.patch.object(yorum, "istek", return_value={"username": yorum.BIZIM}):
            yorum.hesabi_dogrula("t")

    def test_hatali_yorum_tekrar_denenmez_ve_uc_hatada_durur(self):
        cagrilar = []

        def sahte(yol, token, veri=None):
            cagrilar.append(yol)
            raise yorum.Hata("500 x")

        yorumlar = [y("yorgun", username=f"k{i}", id=str(i)) for i in range(5)]
        with mock.patch.object(yorum, "istek", sahte), mock.patch.object(yorum.time, "sleep"):
            with self.assertRaises(yorum.Durdur):
                yorum.calistir([(None, yorumlar)], VERI, "t", SIMDI, False)
        self.assertEqual(len(cagrilar), yorum.EN_COK_HATA)
        self.assertEqual(len(set(cagrilar)), yorum.EN_COK_HATA)

    def test_cursor_url_encode(self):
        yollar = []

        def sahte(yol, token, veri=None):
            yollar.append(yol)
            if len(yollar) == 1:
                return {"data": [], "paging": {"cursors": {"after": "a b&c="}, "next": "x"}}
            return {"data": []}

        with mock.patch.object(yorum, "istek", sahte):
            yorum.yorumlari_al("m", "t")
        self.assertIn("after=a%20b%26c%3D", yollar[1])


if __name__ == "__main__":
    unittest.main()
