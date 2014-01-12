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

        af = ass.ASSFile.parse_file(StringIO(contents))
        out = StringIO()
        af.dump_file(out)

        self.assertEquals(out.getvalue().strip(), contents.strip())

if __name__ == "__main__":
    unittest.main()
