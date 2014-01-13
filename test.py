#!/usr/bin/env python

import ass
import unittest

try:
    from StringIO import StringIO
except:
    from io import StringIO

class TestEverything(unittest.TestCase):
    def test_parse_dump(self):
        with open("test.ass", "r") as f:
            contents = f.read()

        doc = ass.parse(StringIO(contents))
        out = StringIO()
        doc.dump_file(out)

        self.assertEqual(out.getvalue().strip(), contents.strip())

if __name__ == "__main__":
    unittest.main()
