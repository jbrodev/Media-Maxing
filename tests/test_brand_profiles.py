import tempfile
import unittest
from pathlib import Path

from scripts.db.brand_profiles import (
    BrandProfileValidationError,
    create_brand_profile,
    get_brand_profile,
    list_brand_profiles,
    update_brand_profile,
)
from scripts.db.init_db import initialize_database
from scripts.db.seed_demo import DEMO_BRAND_ID, seed_demo_database


class BrandProfileServiceTest(unittest.TestCase):
    def test_create_read_update_and_list_brand_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)

            created = create_brand_profile(
                db_path,
                {
                    "businessName": "North Star Exterior Demo",
                    "tagline": "Careful exterior cleaning for local homes.",
                    "industry": "Exterior cleaning",
                    "description": "Fake demo profile for local-first development.",
                    "services": ["pressure washing", "gutter cleaning"],
                    "serviceAreas": ["Demo City", "Example County"],
                    "targetCustomers": ["homeowners", "property managers"],
                    "brandVoice": "Helpful, practical, and neighborly.",
                    "toneRules": ["be specific", "avoid hype"],
                    "bannedWords": ["guaranteed"],
                    "preferredWords": ["careful", "local"],
                    "commonCTAs": ["Request an estimate"],
                    "hashtags": ["#DemoBusiness", "#ExteriorCleaning"],
                    "website": "https://example.local",
                    "phone": "555-0100",
                    "email": "hello@example.local",
                    "approvalRules": ["Owner approves every generated draft."],
                    "safetyRules": ["Never invent testimonials."],
                    "examplePosts": ["Demo post: Spring exterior cleaning reminder."],
                },
            )

            loaded = get_brand_profile(db_path, created.id)
            self.assertEqual(loaded, created)
            self.assertEqual(loaded.businessName, "North Star Exterior Demo")
            self.assertEqual(loaded.services, ["pressure washing", "gutter cleaning"])
            self.assertEqual(loaded.targetCustomers, ["homeowners", "property managers"])
            self.assertEqual(loaded.email, "hello@example.local")

            updated = update_brand_profile(
                db_path,
                created.id,
                {
                    "businessName": "North Star Exterior Care",
                    "services": ["soft washing"],
                    "email": "owner@example.local",
                },
            )

            self.assertEqual(updated.businessName, "North Star Exterior Care")
            self.assertEqual(updated.services, ["soft washing"])
            self.assertEqual(updated.email, "owner@example.local")

            profiles = list_brand_profiles(db_path)
            self.assertEqual([profile.id for profile in profiles], [created.id])

    def test_brand_profile_validation_rejects_bad_business_name_and_email(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)

            with self.assertRaises(BrandProfileValidationError) as empty_name_error:
                create_brand_profile(db_path, {"businessName": "   "})

            self.assertIn("businessName", str(empty_name_error.exception))

            with self.assertRaises(BrandProfileValidationError) as email_error:
                create_brand_profile(
                    db_path,
                    {
                        "businessName": "Bad Email Demo",
                        "email": "not-an-email",
                    },
                )

            self.assertIn("email", str(email_error.exception))

    def test_seed_demo_database_creates_readable_sample_brand_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            seed_demo_database(db_path)
            profile = get_brand_profile(db_path, DEMO_BRAND_ID)

            self.assertEqual(profile.businessName, "Brightside Exterior Care Demo")
            self.assertEqual(profile.industry, "Exterior cleaning")
            self.assertIn("pressure washing", profile.services)
            self.assertIn("Never invent testimonials.", profile.safetyRules)


if __name__ == "__main__":
    unittest.main()
