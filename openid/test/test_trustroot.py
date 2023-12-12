from __future__ import unicode_literals

import os
import unittest

import six

from openid.server.trustroot import TrustRoot

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'trustroot.txt'), 'rb') as test_data_file:
    trustroot_test_data = test_data_file.read().decode('utf-8')


class ParseTest(unittest.TestCase):

    def test(self):
        ph, pdat, mh, mdat = parseTests(trustroot_test_data)

        for sanity, desc, case in getTests(['bad', 'insane', 'sane'], ph, pdat):
            tr = TrustRoot.parse(case)
            if sanity == 'sane':
                assert tr.isSane(), case
            elif sanity == 'insane':
                assert not tr.isSane(), case
            else:
                assert tr is None, tr

    @unittest.skipUnless(six.PY2, "Test for python 2 only")
    def test_double_port_py2(self):
        # Python 2 urlparse silently drops the ':90' port
        trust_root = TrustRoot.parse('http://*.example.com:80:90/')
        self.assertTrue(trust_root.isSane())
        self.assertEqual(trust_root.buildDiscoveryURL(), 'http://www.example.com/')

    @unittest.skipUnless(six.PY3, "Test for python 3 only")
    def test_double_port_py3(self):
        # Python 3 urllib.parse complains about invalid port
        self.assertIsNone(TrustRoot.parse('http://*.example.com:80:90/'))


class MatchTest(unittest.TestCase):

    def test(self):
        ph, pdat, mh, mdat = parseTests(trustroot_test_data)

        for expected_match, desc, line in getTests([1, 0], mh, mdat):
            tr, rt = line.split()
            tr = TrustRoot.parse(tr)
            self.assertIsNotNone(tr)

            match = tr.validateURL(rt)
            if expected_match:
                assert match
            else:
                assert not match


def getTests(grps, head, dat):
    tests = []
    top = head.strip()
    gdat = [i.strip() for i in dat.split('-' * 40 + '\n')]
    assert not gdat[0]
    assert len(gdat) == (len(grps) * 2 + 1), (gdat, grps)
    i = 1
    for x in grps:
        n, desc = gdat[i].split(': ')
        cases = gdat[i + 1].split('\n')
        assert len(cases) == int(n)
        for case in cases:
            tests.append((x, top + ' - ' + desc, case))
        i += 2
    return tests


def parseTests(data):
    parts = [i.strip() for i in data.split('=' * 40 + '\n')]
    assert not parts[0]
    _, ph, pdat, mh, mdat = parts
    return ph, pdat, mh, mdat
