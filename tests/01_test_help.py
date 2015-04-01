# vim: set fileencoding=utf-8 :

"""Check if --help works"""

from . import context

import unittest

class TestHelp(unittest.TestCase):
    """Test help output of gbp commands"""

    def testHelp(self):
        for script in ['deb.buildpackage',
                       'clone',
                       'config',
                       'create_remote_repo',
                       'deb.dch',
                       'import_orig',
                       'deb.import_dsc',
                       'pull',
                       'deb.pq']:
            module = 'gbp.scripts.%s' % script
            m = __import__(module, globals(), locals(), ['main'], 0)
            self.assertRaises(SystemExit,
                              m.main,
                              ['doesnotmatter', '--help'])

    """Test help output of RPM-specific commands"""
    def testHelpRpm(self):
        for script in ['import_srpm']:
            module = 'gbp.scripts.rpm.%s' % script
            m = __import__(module, globals(), locals(), ['main'], 0)
            self.assertRaises(SystemExit,
                              m.main,
                              ['doesnotmatter', '--help'])

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
