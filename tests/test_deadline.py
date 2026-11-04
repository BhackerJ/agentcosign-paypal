import unittest
from evaluate import constraint_rule


class DeadlineTests(unittest.TestCase):
    def test_delivery_boundaries(self):
        for days, expected in [(7, 'pass'), (14, 'pass'), (15, 'block'), (None, 'insufficient_evidence')]:
            with self.subTest(days=days):
                self.assertEqual(
                    constraint_rule({'operator': 'lte', 'required': 14, 'observed': days}), expected
                )
