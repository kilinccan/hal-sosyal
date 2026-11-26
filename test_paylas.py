"""Ağsız birim testleri: python -X utf8 -m unittest test_paylas"""
import json
import unittest

import paylas

PAGES = "https://x/"


def kayit(**kw):
    k = {"tur": "reel", "dosyalar": ["a.mp4"], "aciklama": "x"}
    k.update(kw)
    return k


class IzlemeTest(unittest.TestCase):
    def test_izleme(self):
        self.assertEqual(paylas.izleme(2500), "2.5")
        self.assertEqual(paylas.izleme(0), "0.0")
        self.assertEqual(paylas.izleme(None), "-")


class PlanlaTest(unittest.TestCase):
    def test_trial_reel(self):
        veri = paylas.planla(kayit(trial=True), PAGES)[0][1]
        self.assertEqual(json.loads(veri["trial_params"]), {"graduation_strategy": "SS_PERFORMANCE"})
        self.assertEqual(veri["thumb_offset"], "2000")

    def test_trialsiz_reel(self):
        self.assertNotIn("trial_params", paylas.planla(kayit(), PAGES)[0][1])

    def test_trial_hikaye_hata(self):
        with self.assertRaisesRegex(paylas.Hata, "trial"):
            paylas.planla(kayit(tur="hikaye", trial=True), PAGES)

    def test_trial_bool_degil_hata(self):
        with self.assertRaisesRegex(paylas.Hata, "trial"):
            paylas.planla(kayit(trial="evet"), PAGES)

    def test_carousel_alt(self):
        plan = paylas.planla(kayit(tur="carousel", dosyalar=["a.png", "b.png"], alt=["bir", "iki"]), PAGES)
        self.assertEqual([p[1].get("alt_text") for p in plan], ["bir", "iki", None])

    def test_alt_hatalari(self):
        for k in (kayit(alt=["x"]), kayit(tur="carousel", dosyalar=["a.png", "b.png"], alt=["x"]),
                  kayit(tur="gorsel", dosyalar=["a.png"], alt=[""])):
            with self.assertRaisesRegex(paylas.Hata, "alt"):
                paylas.planla(k, PAGES)


if __name__ == "__main__":
    unittest.main()
