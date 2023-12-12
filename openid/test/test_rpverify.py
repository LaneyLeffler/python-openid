"""Unit tests for verification of return_to URLs for a realm."""
from __future__ import unicode_literals

import unittest

from mock import patch, sentinel
from testfixtures import LogCapture, StringComparison

from openid.server import trustroot
from openid.server.trustroot import getAllowedReturnURLs
from openid.yadis import services
from openid.yadis.discover import DiscoveryFailure, DiscoveryResult

__all__ = ['TestBuildDiscoveryURL']


class TestBuildDiscoveryURL(unittest.TestCase):
    """Tests for building the discovery URL from a realm and a
    return_to URL
    """

    def assertDiscoveryURL(self, realm, expected_discovery_url):
        """Build a discovery URL out of the realm and a return_to and
        make sure that it matches the expected discovery URL
        """
        realm_obj = trustroot.TrustRoot.parse(realm)
        actual_discovery_url = realm_obj.buildDiscoveryURL()
        self.assertEqual(actual_discovery_url, expected_discovery_url)

    def test_trivial(self):
        """There is no wildcard and the realm is the same as the return_to URL
        """
        self.assertDiscoveryURL('http://example.com/foo', 'http://example.com/foo')

    def test_wildcard(self):
        """There is a wildcard
        """
        self.assertDiscoveryURL('http://*.example.com/foo', 'http://www.example.com/foo')

    def test_wildcard_port(self):
        """There is a wildcard
        """
        self.assertDiscoveryURL('http://*.example.com:8001/foo', 'http://www.example.com:8001/foo')


class TestExtractReturnToURLs(unittest.TestCase):
    disco_url = 'http://example.com/'

    def setUp(self):
        self.original_discover = services.discover
        services.discover = self.mockDiscover
        self.data = None

    def tearDown(self):
        services.discover = self.original_discover

    def mockDiscover(self, uri):
        result = DiscoveryResult(uri)
        result.response_text = self.data
        result.normalized_uri = uri
        return result

    def assertReturnURLs(self, data, expected_return_urls):
        self.data = data
        actual_return_urls = trustroot.getAllowedReturnURLs(self.disco_url)

        self.assertEqual(actual_return_urls, expected_return_urls)

    def assertDiscoveryFailure(self, text):
        self.data = text
        self.assertRaises(DiscoveryFailure, trustroot.getAllowedReturnURLs, self.disco_url)

    def test_empty(self):
        self.assertDiscoveryFailure('')

    def test_badXML(self):
        self.assertDiscoveryFailure('>')

    def test_noEntries(self):
        self.assertReturnURLs(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds"
           xmlns="xri://$xrd*($v*2.0)"
           >
  <XRD>
  </XRD>
</xrds:XRDS>
''', [])

    def test_noReturnToEntries(self):
        self.assertReturnURLs(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds"
           xmlns="xri://$xrd*($v*2.0)"
           >
  <XRD>
    <Service priority="10">
      <Type>http://specs.openid.net/auth/2.0/server</Type>
      <URI>http://www.myopenid.com/server</URI>
    </Service>
  </XRD>
</xrds:XRDS>
''', [])

    def test_oneEntry(self):
        self.assertReturnURLs(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds"
           xmlns="xri://$xrd*($v*2.0)"
           >
  <XRD>
    <Service>
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>http://rp.example.com/return</URI>
    </Service>
  </XRD>
</xrds:XRDS>
''', ['http://rp.example.com/return'])

    def test_twoEntries(self):
        self.assertReturnURLs(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds"
           xmlns="xri://$xrd*($v*2.0)"
           >
  <XRD>
    <Service priority="0">
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>http://rp.example.com/return</URI>
    </Service>
    <Service priority="1">
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>http://other.rp.example.com/return</URI>
    </Service>
  </XRD>
</xrds:XRDS>
''', ['http://rp.example.com/return', 'http://other.rp.example.com/return'])

    def test_twoEntries_withOther(self):
        self.assertReturnURLs(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds"
           xmlns="xri://$xrd*($v*2.0)"
           >
  <XRD>
    <Service priority="0">
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>http://rp.example.com/return</URI>
    </Service>
    <Service priority="1">
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>http://other.rp.example.com/return</URI>
    </Service>
    <Service priority="0">
      <Type>http://example.com/LOLCATS</Type>
      <URI>http://example.com/invisible+uri</URI>
    </Service>
  </XRD>
</xrds:XRDS>
''', ['http://rp.example.com/return', 'http://other.rp.example.com/return'])


class TestReturnToMatches(unittest.TestCase):
    def test_noEntries(self):
        self.assertFalse(trustroot.returnToMatches([], 'anything'))

    def test_exactMatch(self):
        r = 'http://example.com/return.to'
        self.assertTrue(trustroot.returnToMatches([r], r))

    def test_garbageMatch(self):
        r = 'http://example.com/return.to'
        realm = 'This is not a URL at all. In fact, it has characters, like "<" that are not allowed in URLs'
        self.assertTrue(trustroot.returnToMatches([realm, r], r))

    def test_descendant(self):
        r = 'http://example.com/return.to'
        self.assertTrue(trustroot.returnToMatches([r], 'http://example.com/return.to/user:joe'))

    def test_wildcard(self):
        self.assertFalse(trustroot.returnToMatches(['http://*.example.com/return.to'], 'http://example.com/return.to'))

    def test_noMatch(self):
        r = 'http://example.com/return.to'
        self.assertFalse(trustroot.returnToMatches([r], 'http://example.com/xss_exploit'))


class TestGetAllowedReturnURLs(unittest.TestCase):

    def test_equal(self):
        with patch('openid.yadis.services.getServiceEndpoints', autospec=True,
                   return_value=('http://example.com/', sentinel.endpoints)):
            endpoints = getAllowedReturnURLs('http://example.com/')

        self.assertEqual(endpoints, sentinel.endpoints)

    def test_normalized(self):
        # Test redirect is not reported when the returned URL is normalized.
        with patch('openid.yadis.services.getServiceEndpoints', autospec=True,
                   return_value=('http://example.com/', sentinel.endpoints)):
            endpoints = getAllowedReturnURLs('http://example.com:80')

        self.assertEqual(endpoints, sentinel.endpoints)


class TestVerifyReturnTo(unittest.TestCase):

    def test_bogusRealm(self):
        self.assertFalse(trustroot.verifyReturnTo('', 'http://example.com/'))

    def test_verifyWithDiscoveryCalled(self):
        realm = 'http://*.example.com/'
        return_to = 'http://www.example.com/foo'

        def vrfy(disco_url):
            self.assertEqual(disco_url, 'http://www.example.com/')
            return [return_to]

        with LogCapture() as logbook:
            self.assertTrue(trustroot.verifyReturnTo(realm, return_to, _vrfy=vrfy))
        self.assertEqual(logbook.records, [])

    def test_verifyFailWithDiscoveryCalled(self):
        realm = 'http://*.example.com/'
        return_to = 'http://www.example.com/foo'

        def vrfy(disco_url):
            self.assertEqual(disco_url, 'http://www.example.com/')
            return ['http://something-else.invalid/']

        with LogCapture() as logbook:
            self.assertFalse(trustroot.verifyReturnTo(realm, return_to, _vrfy=vrfy))
        logbook.check(('openid.server.trustroot', 'INFO', StringComparison('Failed to validate return_to .*')))

    def test_verifyFailIfDiscoveryRedirects(self):
        realm = 'http://*.example.com/'
        return_to = 'http://www.example.com/foo'

        def vrfy(disco_url):
            raise trustroot.RealmVerificationRedirected(
                disco_url, "http://redirected.invalid")

        with LogCapture() as logbook:
            self.assertFalse(trustroot.verifyReturnTo(realm, return_to, _vrfy=vrfy))
        logbook.check(('openid.server.trustroot', 'INFO', StringComparison('Attempting to verify .*')))


if __name__ == '__main__':
    unittest.main()
