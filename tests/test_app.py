import unittest

from src.app import TransactionRequest, build_feature_vector


class FeatureVectorTests(unittest.TestCase):
    def test_build_feature_vector_includes_all_expected_interaction_features(self):
        tx = TransactionRequest(
            customer_id="cust-001",
            failed_attempts=1,
            is_night_transaction=1,
            is_international=0,
            pin_changed_recently=1,
            merchant_category="ATM Withdrawal",
            transaction_amount=100.0,
            account_balance=1000.0,
            credit_score=700,
            distance_from_home_km=4.0,
            time_since_last_txn_hrs=2.0,
            hour_of_day=22,
            is_weekend=1,
            customer_age=32,
            num_prev_transactions=3,
            transaction_freq_monthly=6,
            country="USA",
            city="New York",
            payment_method="Credit Card",
            device_type="Mobile",
        )

        feature_vector = build_feature_vector(tx, {}, {"features": []})

        self.assertIn("failed_night_pin", feature_vector)
        self.assertIn("night_x_highrisk", feature_vector)
        self.assertEqual(feature_vector["failed_night_pin"], 1)
        self.assertEqual(feature_vector["night_x_highrisk"], 1)


if __name__ == "__main__":
    unittest.main()
