"""Ağsız birim testleri: python -X utf8 -m unittest test_reklam"""
import io
import json
import unittest
from datetime import date, datetime, timezone

import reklam

BUGUN = date(2099, 1, 1)
DURUM0 = {"reklamlar": {}}


def oge(**kw):
    o = {"ad": "tanitim-1", "medya_id": "123", "hedef": "profil_ziyareti", "gunluk_tl": 50,
         "baslangic": "2099-01-01", "bitis": "2099-01-04", "durum": "aktif"}
    o.update(kw)
    return o


def kontrol(ogeler, durum=None, harcanan=0.0):
    reklam.dogrula({"reklamlar": ogeler}, durum or {"reklamlar": {}}, BUGUN, harcanan)


class DogrulaTest(unittest.TestCase):
    def test_gecerli_plan(self):
        kontrol([oge()])

    def test_butce_asimi_planli(self):
        with self.assertRaisesRegex(reklam.Hata, "bütçe"):
            kontrol([oge(gunluk_tl=90, bitis="2099-01-07")])

    def test_butce_asim_payi_ve_harcanan(self):
        kontrol([oge()], harcanan=250)  # 250 + 200*1.25 = 500
        with self.assertRaisesRegex(reklam.Hata, "bütçe"):
            kontrol([oge()], harcanan=251)

    def test_gunluk_toplam_asimi(self):
        kontrol([oge(), oge(ad="ikinci-1", medya_id="9")])  # 100 TL sınırda
        with self.assertRaisesRegex(reklam.Hata, "günlük toplam"):
            kontrol([oge(gunluk_tl=60), oge(ad="ikinci-1", medya_id="9", gunluk_tl=60)])

    def test_sure_ve_gecmis(self):
        with self.assertRaisesRegex(reklam.Hata, "süre"):
            kontrol([oge(bitis="2099-01-08")])
        with self.assertRaisesRegex(reklam.Hata, "geçmişte"):
            kontrol([oge(baslangic="2098-12-30", bitis="2098-12-31")])

    def test_bozuk_girdi(self):
        for kotu in ("x", oge(medya_id="12a"), oge(kuyruk="2099-01-01-0900"), oge(ad="A!"), oge(baslangic="dun"),
                     oge(gunluk_tl=500), oge(hedef="x"), oge(yas_min=10)):
            with self.subTest(kotu=kotu), self.assertRaises(reklam.Hata):
                kontrol([kotu])

    def test_app_store_link(self):
        link = "https://apps.apple.com/tr/app/hal/id6700000000?ct=ig_ad"
        kontrol([oge(hedef="app_store", link=link)])
        for o in (oge(hedef="app_store"), oge(link=link),
                  oge(hedef="app_store", link="https://ornek.com/id1"),
                  oge(hedef="app_store", link="https://apps.apple.com/tr/app/hal/id1 x")):
            with self.assertRaises(reklam.Hata):
                kontrol([o])

    def test_degismez_alan(self):
        durum = {"reklamlar": {"tanitim-1": {"plan": {"medya_id": "123", "hedef": "erisim"}}}}
        with self.assertRaisesRegex(reklam.Hata, "hedef"):
            kontrol([oge()], durum)

    def test_durum_dosyasi_kimlik(self):
        with self.assertRaises(reklam.Hata):
            reklam.durum_dogrula({"reklamlar": {"a": {"plan": {}, "adset": "../x"}}})


class UzlastirTest(unittest.TestCase):
    def ctx(self):
        self.cagrilar = []

        def post(yol, veri):
            self.cagrilar.append((yol, veri))
            return {"id": str(len(self.cagrilar))}
        return {"post": post, "al": lambda yol: {"data": []}, "hesap": "1", "sayfa": "2", "ig": "3", "token": None,
                "simdi": datetime(2099, 1, 1, tzinfo=timezone.utc)}

    def test_plandan_silinen_durdurulur(self):
        durum = {"reklamlar": {"eski-1": {"plan": {}, "kampanya": "10", "adset": "11", "reklam": "12", "durum_meta": "ACTIVE"}}}
        reklam.uzlastir({"reklamlar": []}, durum, self.ctx(), lambda: None)
        self.assertEqual([c[0] for c in self.cagrilar], ["12", "11", "10"])
        self.assertTrue(all(c[1] == {"status": "PAUSED"} for c in self.cagrilar))
        self.assertEqual(durum["reklamlar"]["eski-1"]["durum_meta"], "PAUSED")

    def test_yarim_kalan_durum_devam_eder(self):
        durum = {"reklamlar": {"tanitim-1": {"plan": {}, "medya": "123", "kampanya": "10", "adset": "11"}}}
        reklam.uzlastir({"reklamlar": [oge()]}, durum, self.ctx(), lambda: None)
        yollar = [c[0] for c in self.cagrilar]
        self.assertNotIn("act_1/campaigns", yollar)
        self.assertNotIn("act_1/adsets", yollar)
        self.assertEqual(yollar[:2], ["act_1/adcreatives", "act_1/ads"])
        self.assertEqual(durum["reklamlar"]["tanitim-1"]["durum_meta"], "ACTIVE")

    def test_yeni_reklam_once_paused(self):
        durum = {"reklamlar": {}}
        reklam.uzlastir({"reklamlar": [oge()]}, durum, self.ctx(), lambda: None)
        olusturma = [c for c in self.cagrilar if c[1].get("status") == "PAUSED" and "/" in c[0]]
        self.assertEqual(len(olusturma), 3)  # kampanya, adset, reklam
        self.assertEqual(self.cagrilar[-1][1], {"status": "ACTIVE"})


class MetaHatasi(unittest.TestCase):
    def coz(self, **ek):
        govde = json.dumps({"error": {"code": 100, "message": "Invalid parameter", **ek}}).encode()
        return reklam.meta_hatasi(io.BytesIO(govde))

    def test_meta_hata_ayrintisi(self):
        alan = {"blame_field_specs": [["daily_budget"]]}
        for veri in (alan, json.dumps(alan)):
            cikti = self.coz(error_subcode=7, error_data=veri, error_user_msg="GIZLI")
            self.assertEqual(cikti, "code=100 Invalid parameter | subcode=7 | alan=daily_budget")
        for veri in (None, "{bozuk", "metin", [1], {"blame_field_specs": [None]}):
            self.assertEqual(self.coz(error_data=veri), "code=100 Invalid parameter")

    def test_meta_hata_tek_satir(self):
        cikti = self.coz(error_user_title="x\n::warning::y\r\n" + "z" * 500)
        self.assertNotIn("\n", cikti)
        self.assertNotIn("\r", cikti)
        self.assertLessEqual(len(cikti), 300)
        self.assertEqual(reklam.meta_hatasi(io.BytesIO(b'{"error": []}')), "gövde okunamadı")


if __name__ == "__main__":
    unittest.main()
