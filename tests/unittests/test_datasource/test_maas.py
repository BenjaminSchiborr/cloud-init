from copy import copy
import os
import shutil
import tempfile

from cloudinit.sources import DataSourceMAAS
from cloudinit import url_helper
from ..helpers import TestCase, populate_dir

try:
    from unittest import mock
except ImportError:
    import mock


class TestMAASDataSource(TestCase):

    def setUp(self):
        super(TestMAASDataSource, self).setUp()
        # Make a temp directoy for tests to use.
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_seed_dir_valid(self):
        """Verify a valid seeddir is read as such."""

        data = {'instance-id': 'i-valid01',
            'local-hostname': 'valid01-hostname',
            'user-data': b'valid01-userdata',
            'public-keys': 'ssh-rsa AAAAB3Nz...aC1yc2E= keyname'}

        my_d = os.path.join(self.tmp, "valid")
        populate_dir(my_d, data)

        (userdata, metadata) = DataSourceMAAS.read_maas_seed_dir(my_d)

        self.assertEqual(userdata, data['user-data'])
        for key in ('instance-id', 'local-hostname'):
            self.assertEqual(data[key], metadata[key])

        # verify that 'userdata' is not returned as part of the metadata
        self.assertFalse(('user-data' in metadata))

    def test_seed_dir_valid_extra(self):
        """Verify extra files do not affect seed_dir validity."""

        data = {'instance-id': 'i-valid-extra',
            'local-hostname': 'valid-extra-hostname',
            'user-data': b'valid-extra-userdata', 'foo': 'bar'}

        my_d = os.path.join(self.tmp, "valid_extra")
        populate_dir(my_d, data)

        (userdata, metadata) = DataSourceMAAS.read_maas_seed_dir(my_d)

        self.assertEqual(userdata, data['user-data'])
        for key in ('instance-id', 'local-hostname'):
            self.assertEqual(data[key], metadata[key])

        # additional files should not just appear as keys in metadata atm
        self.assertFalse(('foo' in metadata))

    def test_seed_dir_invalid(self):
        """Verify that invalid seed_dir raises MAASSeedDirMalformed."""

        valid = {'instance-id': 'i-instanceid',
            'local-hostname': 'test-hostname', 'user-data': ''}

        my_based = os.path.join(self.tmp, "valid_extra")

        # missing 'userdata' file
        my_d = "%s-01" % my_based
        invalid_data = copy(valid)
        del invalid_data['local-hostname']
        populate_dir(my_d, invalid_data)
        self.assertRaises(DataSourceMAAS.MAASSeedDirMalformed,
                          DataSourceMAAS.read_maas_seed_dir, my_d)

        # missing 'instance-id'
        my_d = "%s-02" % my_based
        invalid_data = copy(valid)
        del invalid_data['instance-id']
        populate_dir(my_d, invalid_data)
        self.assertRaises(DataSourceMAAS.MAASSeedDirMalformed,
                          DataSourceMAAS.read_maas_seed_dir, my_d)

    def test_seed_dir_none(self):
        """Verify that empty seed_dir raises MAASSeedDirNone."""

        my_d = os.path.join(self.tmp, "valid_empty")
        self.assertRaises(DataSourceMAAS.MAASSeedDirNone,
                          DataSourceMAAS.read_maas_seed_dir, my_d)

    def test_seed_dir_missing(self):
        """Verify that missing seed_dir raises MAASSeedDirNone."""
        self.assertRaises(DataSourceMAAS.MAASSeedDirNone,
            DataSourceMAAS.read_maas_seed_dir,
            os.path.join(self.tmp, "nonexistantdirectory"))

    def test_seed_url_valid(self):
        """Verify that valid seed_url is read as such."""
        valid = {
            'meta-data/instance-id': 'i-instanceid',
            'meta-data/local-hostname': 'test-hostname',
            'meta-data/public-keys': 'test-hostname',
            'user-data': b'foodata',
            }
        valid_order = [
            'meta-data/local-hostname',
            'meta-data/instance-id',
            'meta-data/public-keys',
            'user-data',
            ]
        my_seed = "http://example.com/xmeta"
        my_ver = "1999-99-99"
        my_headers = {'header1': 'value1', 'header2': 'value2'}

        def my_headers_cb(url):
            return my_headers

        # Each time url_helper.readurl() is called, something different is
        # returned based on the canned data above.  We need to build up a list
        # of side effect return values, which the mock will return.  At the
        # same time, we'll build up a list of expected call arguments for
        # asserting after the code under test is run.
        calls = []

        def side_effect():
            for key in valid_order:
                resp = valid.get(key)
                url = "%s/%s/%s" % (my_seed, my_ver, key)
                calls.append(
                    mock.call(url, headers=None, timeout=mock.ANY,
                              data=mock.ANY, sec_between=mock.ANY,
                              ssl_details=mock.ANY, retries=mock.ANY,
                              headers_cb=my_headers_cb,
                              exception_cb=mock.ANY))
                yield url_helper.StringResponse(resp)

        # Now do the actual call of the code under test.
        with mock.patch.object(url_helper, 'readurl',
                               side_effect=side_effect()) as mockobj:
            userdata, metadata = DataSourceMAAS.read_maas_seed_url(
                my_seed, version=my_ver)

            self.assertEqual(b"foodata", userdata)
            self.assertEqual(metadata['instance-id'],
                             valid['meta-data/instance-id'])
            self.assertEqual(metadata['local-hostname'],
                             valid['meta-data/local-hostname'])

            mockobj.has_calls(calls)

    def test_seed_url_invalid(self):
        """Verify that invalid seed_url raises MAASSeedDirMalformed."""
        pass

    def test_seed_url_missing(self):
        """Verify seed_url with no found entries raises MAASSeedDirNone."""
        pass


# vi: ts=4 expandtab
