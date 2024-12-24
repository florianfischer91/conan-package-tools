
__version__ = '0.200.0'


def get_client_version():
    from conan import conan_version
    from cpt._compat import Version
    return Version(str(conan_version).replace("-dev", ""))
