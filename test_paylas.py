"""Ağsız birim testleri: python -X utf8 -m unittest test_paylas"""
import json
import unittest

import paylas

PAGES = "https://x/"


def kayit(**kw):
    k = {"tur": "reel", "dosyalar": ["a.mp4"], "aciklama": "x"}
    k.update(kw)
    return k


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


if __name__ == "__main__":
    unittest.main()
