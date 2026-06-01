import unittest

from scripts.ai.safety import run_safety_checks


def _brand(**overrides):
    base = {
        "id": "brand-test",
        "businessName": "Brightside Exterior Care Demo",
        "supportedClaims": [],
        "blockedPhrases": [],
    }
    base.update(overrides)
    return base


class CleanCaptionTest(unittest.TestCase):
    def test_clean_caption_emits_no_flags(self):
        flags, blocking, fixes = run_safety_checks(
            "Today we focused on a careful surface check before pressure washing the driveway.",
            _brand(),
        )
        self.assertEqual(flags, [])
        self.assertEqual(blocking, [])
        self.assertEqual(fixes, [])


class GuaranteeTest(unittest.TestCase):
    def test_guarantee_flagged_and_blocking(self):
        flags, blocking, _ = run_safety_checks(
            "We guarantee a spotless driveway every time.", _brand()
        )
        self.assertIn("unsupported_guarantee", flags)
        self.assertIn("unsupported_guarantee", blocking)

    def test_hundred_percent_satisfaction_flagged(self):
        flags, blocking, _ = run_safety_checks(
            "100% satisfaction on every job, or your money back.", _brand()
        )
        self.assertIn("unsupported_guarantee", flags)
        self.assertIn("unsupported_guarantee", blocking)


class TestimonialTest(unittest.TestCase):
    def test_invented_testimonial_flagged(self):
        flags, blocking, _ = run_safety_checks(
            "One customer said: 'Best job I've ever seen!'", _brand()
        )
        self.assertIn("fake_testimonial", flags)
        self.assertIn("fake_testimonial", blocking)


class CredentialTest(unittest.TestCase):
    def test_unsupported_license_flagged(self):
        flags, blocking, _ = run_safety_checks(
            "We are a fully licensed and insured local team.", _brand()
        )
        self.assertIn("unsupported_claim", flags)
        self.assertIn("unsupported_claim", blocking)

    def test_supported_credential_not_flagged(self):
        flags, _, _ = run_safety_checks(
            "We are a fully licensed local team.",
            _brand(supportedClaims=["Fully licensed for residential exterior work"]),
        )
        self.assertNotIn("unsupported_claim", flags)


class BlockedPhraseTest(unittest.TestCase):
    def test_blocked_phrase_flagged_and_blocking(self):
        flags, blocking, fixes = run_safety_checks(
            "The best in town, hands down.",
            _brand(blockedPhrases=["best in town"]),
        )
        self.assertIn("brand_mismatch", flags)
        self.assertIn("brand_mismatch", blocking)
        self.assertTrue(any("best in town" in fix for fix in fixes))


class AggressiveLanguageTest(unittest.TestCase):
    def test_pressure_phrase_flagged_non_blocking(self):
        flags, blocking, _ = run_safety_checks(
            "Act now! Last chance to book before next week.", _brand()
        )
        self.assertIn("aggressive_language", flags)
        # Aggressive language is non-blocking by design — the owner may
        # still want to ship it in some cases.
        self.assertNotIn("aggressive_language", blocking)


class PublishedClaimTest(unittest.TestCase):
    def test_already_posted_claim_flagged_and_blocking(self):
        flags, blocking, _ = run_safety_checks(
            "We posted this update earlier today.", _brand()
        )
        self.assertIn("platform_policy_risk", flags)
        self.assertIn("platform_policy_risk", blocking)


class ApprovalBypassTest(unittest.TestCase):
    def test_bypass_phrase_flagged_and_blocking(self):
        flags, blocking, _ = run_safety_checks(
            "Auto-approved by the marketing system, sending now.", _brand()
        )
        self.assertIn("missing_approval", flags)
        self.assertIn("missing_approval", blocking)


class EmergencyPauseTest(unittest.TestCase):
    def test_emergency_pause_adds_informational_flag(self):
        flags, blocking, fixes = run_safety_checks(
            "A normal clean caption.", _brand(), emergency_pause_enabled=True
        )
        self.assertIn("emergency_pause_conflict", flags)
        # Not blocking: generation is allowed under pause; scheduling is not.
        self.assertNotIn("emergency_pause_conflict", blocking)
        self.assertTrue(any("Emergency pause" in fix for fix in fixes))

    def test_no_pause_no_flag(self):
        flags, _, _ = run_safety_checks(
            "A normal clean caption.", _brand(), emergency_pause_enabled=False
        )
        self.assertNotIn("emergency_pause_conflict", flags)


class InvariantsTest(unittest.TestCase):
    def test_blocking_is_always_subset_of_flags(self):
        captions = [
            "We guarantee results and we are licensed and insured.",
            "Auto-approved. Don't miss out. Hurry!",
            "Best in town with 100% satisfaction guarantee.",
        ]
        for caption in captions:
            with self.subTest(caption=caption):
                flags, blocking, _ = run_safety_checks(
                    caption,
                    _brand(blockedPhrases=["best in town"]),
                )
                self.assertTrue(set(blocking).issubset(set(flags)))


if __name__ == "__main__":
    unittest.main()
