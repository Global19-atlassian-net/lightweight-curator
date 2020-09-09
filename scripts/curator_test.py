from curator import prepare_valid_indices_names
from freezegun import freeze_time
import unittest

class TestMethods(unittest.TestCase):

    @freeze_time("2018-01-01")
    def test_get_valid_indices(self):
        # this is how our result should look like
        inset = set(["foo-2018.01.01", "foo-2017.12.31", "foo-2017.12.30"])
        outset = prepare_valid_indices_names("foo-", 3, "%Y.%m.%d")
        self.assertEqual(inset, outset)

if __name__ == '__main__':
    unittest.main()
