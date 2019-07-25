# coding=utf-8

import re
import semver

from devpi_plumber.client import volatile_index

_TAR_GZ_END = '.tar.gz'
_TAR_BZ2_END = '.tar.bz2'
_ZIP_END = '.zip'


def _extract_name_and_version(filename):
    if filename.endswith('.whl') or filename.endswith('.egg'):
        return filename.split('-')[:2]
    else:
        name, version_and_ext = filename.rsplit('-', 1)
        if not version_and_ext[0].isdigit():  # setuptools-scm on old setuptools separates local part via dash.
            parts = filename.split('-')
            name = '-'.join(parts[:-2])
            version_and_ext = '-'.join(parts[-2:])
        for extension in (_TAR_GZ_END, _TAR_BZ2_END, _ZIP_END):
            if version_and_ext.endswith(extension):
                return name, version_and_ext[:-len(extension)]
        raise NotImplementedError('Unknown package type. Cannot extract version from {}.'.format(filename))


class Package(object):
    def __init__(self, package_url):
        parts = package_url.rsplit('/', 6)  # example URL http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz
        self.index = parts[1] + '/' + parts[2]
        self.name, self.version = _extract_name_and_version(parts[-1])

    def __str__(self):
        return '{package} {version} on {index}'.format(
            package=self.name,
            version=self.version,
            index=self.index,
        )

    @property
    def is_dev_package(self):
        return '.dev' in self.version

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name and self.version == other.version

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.index, self.name, self.version))

    def __gt__(self, other):
        result = self.index == other.index and self.name == other.name
        try:
            result = result and semver.compare(self.version, other.version) > 0
        except ValueError as e:
            result = result and self.version > other.version
        return result

    def __lt__(self, other):
        result = self.index == other.index and self.name == other.name
        try:
            result = result and semver.compare(self.version, other.version) < 0
        except ValueError as e:
            result = result and self.version < other.version
        return result


def _list_packages_on_index(client, index, package_spec, only_dev, version_filter):
    if version_filter is not None:
        version_filter = re.compile(version_filter)

    def selector(package):
        return (
            package.index == index and
            (not only_dev or package.is_dev_package) and
            (version_filter is None or version_filter.search(package.version))
        )

    client.use(index)

    all_packages = {
        Package(package_url) for package_url in client.list('--index', index, '--all', package_spec)
        if package_url.startswith('http://') or package_url.startswith('https://')
    }

    return set(filter(selector, all_packages))


def _get_indices(client, index_spec):
    spec_parts = index_spec.split('/')
    if len(spec_parts) > 1:
        return [index_spec, ]
    else:
        return client.list_indices(user=index_spec)


def list_packages_by_index(client, index_spec, package_spec, only_dev, version_filter):
    return {
        index: _list_packages_on_index(client, index, package_spec, only_dev, version_filter)
        for index in _get_indices(client, index_spec)
    }


def remove_packages(client, index, packages, force, versions_to_keep = 0):
    versions_deleted = 0
    num_of_packages = len(packages)
    print ("num of packages: {}".format(num_of_packages))
    sorted_packages = sorted(packages)
    with volatile_index(client, index, force):
        for package in sorted_packages:
            assert package.index == index
            print (package)
            if num_of_packages - versions_deleted > versions_to_keep:
                print ("deleting {name}=={version}".format(name=package.name, version=package.version))
                client.remove('--index', package.index, '{name}=={version}'.format(name=package.name, version=package.version))
                print("deleted {name}=={version}".format(name=package.name, version=package.version))
                versions_deleted += 1
            else:
                print ("deleted {}, leaving {} versions".format(versions_deleted, versions_to_keep))
                return
