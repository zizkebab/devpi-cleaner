# coding=utf-8

import unittest

from mock import Mock

from devpi_plumber.client import DevpiCommandWrapper

from devpi_cleaner.client import list_packages, Package


class ClientTests(unittest.TestCase):
    def test_list_packages(self):
        expected_packages = [
            'http://dummy-server/nutzer/eins/+f/70e/3bc67b3194143/paket-1.0.tar.gz',
            'http://dummy-server/nutzer/zwei/+f/70e/3bc67b3194144/paket-2.0.tar.gz',
        ]

        devpi_client = Mock(spec=DevpiCommandWrapper)
        devpi_client.user = 'nutzer'
        devpi_client.list_indices.return_value = ['eins', 'zwei']
        devpi_client.list.side_effect = [[package] for package in expected_packages]
        devpi_client.url = 'http://dummy-server/nutzer'

        actual_packages = list_packages(devpi_client, 'paket', only_dev=False)
        self.assertEqual(expected_packages, [str(package) for package in actual_packages])

    def test_list_packages_filters(self):
        """
        The package list must be stripped from inherited packages and [*redirected] messages
        """
        devpi_listing = [
            '*redirected: http://localhost:2414/user/index2/delete_me',
            'http://localhost:2414/user/index2/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl',
            'http://localhost:2414/user/index2/+f/313/8642d2b43a764/delete_me-0.2.tar.gz',
            'http://localhost:2414/other_user/index1/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl',
            'http://localhost:2414/other_user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz'
        ]
        expected_packages = [
            'http://localhost:2414/user/index2/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl',
            'http://localhost:2414/user/index2/+f/313/8642d2b43a764/delete_me-0.2.tar.gz',
        ]

        devpi_client = Mock(spec=DevpiCommandWrapper)
        devpi_client.user = 'user'
        devpi_client.url = 'http://localhost:2414/user/index2'
        devpi_client.list_indices.return_value = ['index2']
        devpi_client.list.return_value = devpi_listing

        actual_packages = list_packages(devpi_client, 'delete_me', only_dev=False)
        self.assertEqual(expected_packages, [str(package) for package in actual_packages])

        devpi_client.list.assert_called_once_with('--all', 'delete_me')  # `--all` is important as otherwise not all packages will be returned

    def test_list_only_dev_packages(self):
        devpi_listing = [
            'http://localhost:2414/user/index1/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl',
            'http://localhost:2414/user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz',
            'http://localhost:2414/user/index1/+f/bab/f9b37c9d0d192/delete_me-0.2a1.tar.gz',
            'http://localhost:2414/user/index1/+f/e8e/d9cfe14d2ef65/delete_me-0.2a1-py2.py3-none-any.whl',
            'http://localhost:2414/user/index1/+f/842/84d1283874110/delete_me-0.2.dev2.tar.gz',
            'http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl',
            'http://localhost:2414/user/index1/+f/c22/cdec16d5ddc3a/delete_me-0.1-py2.py3-none-any.whl',
            'http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz',
        ]
        expected_packages = [
            'http://localhost:2414/user/index1/+f/842/84d1283874110/delete_me-0.2.dev2.tar.gz',
            'http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl',
        ]

        devpi_client = Mock(spec=DevpiCommandWrapper)
        devpi_client.user = 'user'
        devpi_client.url = 'http://localhost:2414/user/index1'
        devpi_client.list_indices.return_value = ['index1']
        devpi_client.list.return_value = devpi_listing

        actual_packages = list_packages(devpi_client, 'delete_me', only_dev=True)
        self.assertEqual(expected_packages, [str(package) for package in actual_packages])


class PackageTests(unittest.TestCase):
    def test_sdist(self):
        package = Package('http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz')
        self.assertEquals('user/index1', package.index)
        self.assertEquals('delete_me', package.name)
        self.assertEquals('0.1', package.version)
        self.assertFalse(package.is_dev_package)

        zip_package = Package('http://localhost:2414/user/index1/+f/45b/301745c6d8bbe/delete_me-0.1.zip')
        self.assertEquals('0.1', zip_package.version)

    def test_wheel(self):
        package = Package('http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl')
        self.assertEquals('user/index1', package.index)
        self.assertEquals('delete_me', package.name)
        self.assertEquals('0.2.dev2', package.version)
        self.assertTrue(package.is_dev_package)

    def test_unkown_format(self):
        with self.assertRaises(NotImplementedError):
            Package('http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.unkown')

