import unittest
from datetime import date, timedelta
from recovery_dates import recovery_dates


class RecoveryDatesTest(unittest.TestCase):
    def test_every_weekday_includes_today_in_one_three_date_local_week(self):
        for monday in (date(2026, 10, 26), date(2026, 12, 28)):
            for weekday in range(7):
                today = monday + timedelta(days=weekday)
                with self.subTest(today=today):
                    selected = recovery_dates(today)
                    self.assertIn(today, selected)
                    self.assertEqual(len(set(selected)), 3)
                    self.assertEqual(selected, sorted(selected))
                    self.assertTrue(all(d - timedelta(days=d.weekday()) == monday for d in selected))
                    self.assertTrue(all((b - a).days >= 2 for a, b in zip(selected, selected[1:])))


if __name__ == '__main__':
    unittest.main()
