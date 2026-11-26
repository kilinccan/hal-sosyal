"""Ağsız birim testleri: python -X utf8 -m unittest test_yorum"""
import json
import unittest
from datetime import datetime, timezone

import yorum

VERI = json.loads(yorum.VERI.read_text(encoding="utf-8"))
SIMDI = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def y(text, username="u", id="1", ts="2026-11-26T10:00:00+0000", **kw):
    return {"id": id, "text": text, "username": username, "timestamp": ts, **kw}


def ihtiyac_adi(text):
    return yorum.cevap_metni(y(text), VERI)[0]


class Esleme(unittest.TestCase):
    def test_anahtar_kelimeler(self):
        for metin, beklenen in [("Yorgunum", "yorgun"), ("KAYGILI", "kaygi"), ("endişeli", "kaygi"),
                                ("Kırgın", "uzgun"), ("İyi değilim", "uzgun"), ("Şükür", "sukur"),
                                ("iyiyim", "sukur"), ("yalnızım", "yalniz"), ("sabır", "sabir"),
                                ("umut", "umut"), ("korkuyorum", "korku"), ("öfkeliyim", "ofke")]:
            with self.subTest(metin):
                self.assertEqual(ihtiyac_adi(metin), beklenen)

    def test_eslesme_yoksa_genel(self):
        self.assertEqual(ihtiyac_adi("hmm"), "genel")

    def test_cevap_bicimi_ve_sinir(self):
        _, m = yorum.cevap_metni(y("yorgun", username="ayse"), VERI)
        self.assertTrue(m.startswith("@ayse Hâline iyi gelsin: «") and m.endswith("🤍"))
        for ad, liste in VERI["ayetler"].items():
            for i, a in enumerate(liste):
                self.assertLessEqual(len(a["meal"]), 200, ad)
                m = yorum.cevap_metni(y("yorgun", username="x" * 30, id=str(i)), VERI)[1]
                self.assertLessEqual(len(m), 300)

    def test_her_ihtiyacin_ayeti_var(self):
        for ad, _ in yorum.ANAHTAR:
            self.assertTrue(3 <= len(VERI["ayetler"][ad]) <= 5, ad)
        self.assertTrue(3 <= len(VERI["ayetler"]["genel"]) <= 5)


class Kriz(unittest.TestCase):
    def test_kriz_ayetsiz_destek(self):
        for metin in ["ölmek istiyorum", "Kendime zarar vermek istiyorum", "yaşamak istemiyorum", "intihar"]:
            ad, m = yorum.cevap_metni(y(metin, username="u"), VERI)
            self.assertEqual(ad, "kriz")
            self.assertIn("112", m)
            self.assertNotIn("«", m)
            self.assertLessEqual(len(m), 300)

    def test_kriz_ihtiyac_kelimesinden_once(self):
        self.assertEqual(ihtiyac_adi("yorgunum ölmek istiyorum"), "kriz")

    def test_uzun_krizli_yorum_yine_destek(self):
        self.assertEqual(ihtiyac_adi("çok zor günler geçiriyorum artık kendime zarar vermek istiyorum"), "kriz")


class Atlama(unittest.TestCase):
    def test_uzun_linkli_hakaret_atlanir(self):
        for metin in ["a" * 61, "bak https://x.co", "www.site.com", "@baskasi yorgun", "salak"]:
            with self.subTest(metin):
                self.assertIsNone(yorum.cevap_metni(y(metin), VERI))

    def test_60_karakter_serbest(self):
        self.assertIsNotNone(yorum.cevap_metni(y("yorgun " + "a" * 53), VERI))

    def test_zaten_cevaplanmis_atlanir(self):
        cevapli = y("yorgun", replies={"data": [{"username": yorum.BIZIM, "timestamp": "2026-11-26T11:00:00+0000"}]})
        self.assertEqual(yorum.secilenler([cevapli, y("kaygı", username="v", id="2")], SIMDI)[0]["id"], "2")
        self.assertEqual(len(yorum.secilenler([cevapli], SIMDI)), 0)

    def test_ayni_kisiye_gunde_tek_cevap(self):
        self.assertEqual(len(yorum.secilenler([y("yorgun", id="1"), y("kaygı", id="2")], SIMDI)), 1)
        onceki = y("yorgun", id="1", replies={"data": [{"username": yorum.BIZIM, "timestamp": "2026-11-26T11:00:00+0000"}]})
        self.assertEqual(len(yorum.secilenler([onceki, y("kaygı", id="2")], SIMDI)), 0)

    def test_eski_ve_kendi_yorumumuz_atlanir(self):
        self.assertEqual(yorum.secilenler([y("yorgun", ts="2026-11-01T10:00:00+0000"),
                                           y("yorgun", username=yorum.BIZIM, id="3")], SIMDI), [])


class Calistirma(unittest.TestCase):
    def test_kuru_ag_yok_ve_cevap_sinirli(self):
        yorumlar = [y("yorgun", username=f"k{i}", id=str(i)) for i in range(40)]
        sayac, hata = yorum.calistir([yorumlar], VERI, None, SIMDI, True)
        self.assertEqual((sayac["cevap"], sayac["sinir"], hata), (yorum.EN_COK_CEVAP, 10, 0))


if __name__ == "__main__":
    unittest.main()
