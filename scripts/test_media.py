"""Run conversion regression tests against the media binaries being shipped."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
suffix = '.exe' if os.name == 'nt' else ''
suite = unittest.TestSuite([
    unittest.defaultTestLoader.loadTestsFromName('test_converter'),
    unittest.defaultTestLoader.loadTestsFromName('test_portability.ConversionEdgeTests'),
])
with patch('converter.find_tool', side_effect=lambda name: root / 'vendor' / 'bin' / (name + suffix)):
    result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
