import unittest
import os
import zipfile
import textwrap

from conans.model.manifest import FileTreeManifest

from cpt.test.utils.tools import TestClient, TestServer, pos_args
from cpt.test.unit.utils import MockCIManager

from cpt.test.test_client.tools import get_patched_multipackager
from cpt._compat import CONAN_V2, environment_append, PackageReference

class UploadTest(unittest.TestCase):

    conanfile = """from conan import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build(self):
        self.output.warning("HALLO")
"""

    def setUp(self):
        for var in ["CONAN_USERNAME", "CONAN_CHANNEL", "CONAN_REFERENCE"]:
            try:
                del os.environ[var]
            except:
                pass
        self._ci_manager = MockCIManager()

    def test_dont_upload_non_built_packages(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertIn("Uploading package 1/2", out)
                self.assertIn("Uploading package 2/2", out)

            # With the same cache and server try to rebuild them with policy missing
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Skipping upload for 55c609fe8808aa5308134cb5989d23d3caffccf2", out)
                self.assertIn("Skipping upload for 1744785cb24e3bdca70e27041dc5abd20476f947", out)
            else:
                self.assertIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", out)
                self.assertIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", out)
            self.assertNotIn("HALLO", out)

            # Without any build policy they get built
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertNotIn("Skipping upload for 55c609fe8808aa5308134cb5989d23d3caffccf2", out)
                self.assertNotIn("Skipping upload for 1744785cb24e3bdca70e27041dc5abd20476f947", out)
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertNotIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", out)
                self.assertNotIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", out)
                self.assertIn("Uploading package 1/2", out)
                self.assertIn("Uploading package 2/2", out)
            self.assertIn("HALLO", out)

    def test_upload_when_tag_is_false(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        zip_path = os.path.join(tc.current_folder, 'config.zip')
        zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zipf.close()

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_CONFIG_URL": zip_path, "CONAN_UPLOAD_ONLY_WHEN_TAG": "1",
                                 "TRAVIS": "1"}):

            
            mp = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"])
            mp.add_common_builds(shared_option_name=False)
            mp.run()
            out = mp.printer.printer.dump()
            
            if CONAN_V2:
                self.assertNotIn("Redefined channel by branch tag", out)
                self.assertNotIn("Uploading package 'lib/1.0@user/stable#", out)
                self.assertNotRegex(out, r"Uploading package 'lib/1.0@user/stable#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertIn("Skipping upload, not tag branch", out)
            else:
                self.assertNotIn("Redefined channel by branch tag", out)
                self.assertNotIn("Uploading packages for 'lib/1.0@user/stable'", out)
                self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9 to 'default'", out)
                self.assertIn("Skipping upload, not tag branch", out)

    def test_upload_when_tag_is_true(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        zip_path = os.path.join(tc.current_folder, 'config.zip')
        zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zipf.close()

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_CONFIG_URL": zip_path, "CONAN_UPLOAD_ONLY_WHEN_TAG": "1",
                                 "TRAVIS": "1", "TRAVIS_TAG": "0.1"}):

            
            mp = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"])
            mp.add_common_builds(shared_option_name=False)
            mp.run()
            out = mp.printer.printer.dump()
            
            if CONAN_V2:
                self.assertNotIn("Skipping upload, not tag branch", out)
                self.assertIn("Redefined channel by branch tag", out)
                self.assertIn("Uploading package 'lib/1.0@user/stable#", out)
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/stable#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
            else:
                self.assertNotIn("Skipping upload, not tag branch", out)
                self.assertIn("Redefined channel by branch tag", out)
                self.assertIn("Uploading packages for 'lib/1.0@user/stable'", out)
                self.assertIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9 to 'default'", out)

    def test_upload_only_recipe_env_var(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        # Upload only the recipe
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_UPLOAD_ONLY_RECIPE": "TRUE", "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel#", out)
                self.assertIn("Uploading to remote default", out)
                self.assertIn("Uploading recipe 'lib/1.0@user/mychannel#", out)
                self.assertNotRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertNotRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", out)
                self.assertIn("Uploading lib/1.0@user/mychannel to remote", out)
                self.assertIn("Uploaded conan recipe 'lib/1.0@user/mychannel'", out)
                self.assertNotIn("Uploading package 1/2", out)
                self.assertNotIn("Uploading package 2/2", out)

        # Re-use cache the upload the binary packages
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_UPLOAD_ONLY_RECIPE": "FALSE", "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel#", out)
                self.assertIn("Uploading to remote default", out)
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", tc.out)
                self.assertIn("Uploading lib/1.0@user/mychannel to remote", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)
                self.assertIn("Uploading package 1/2", out)
                self.assertIn("Uploading package 2/2", out)

    def test_upload_only_recipe_params(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        # Upload only the recipe
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      upload_only_recipe=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel#", out)
                self.assertIn("Uploading to remote default", out)
                self.assertIn("Uploading recipe 'lib/1.0@user/mychannel#", out)
                self.assertNotRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertNotRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", out)
                self.assertIn("Uploading lib/1.0@user/mychannel to remote", out)
                self.assertIn("Uploaded conan recipe 'lib/1.0@user/mychannel'", out)
                self.assertNotIn("Uploading package 1/2", out)
                self.assertNotIn("Uploading package 2/2", out)

        # Re-use cache the upload the binary packages
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      upload_only_recipe=False,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel#", out)
                # self.assertNotIn("Recipe is up to date, upload skipped", out)
                self.assertIn("Uploading to remote default", out)
                self.assertIn("Uploading recipe 'lib/1.0@user/mychannel#", out)
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/mychannel#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", out)
                self.assertIn("Uploading lib/1.0@user/mychannel to remote", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)
                self.assertIn("Uploading package 1/2", out)
                self.assertIn("Uploading package 2/2", out)

    def test_upload_package_revisions(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_REVISIONS_ENABLED": "1"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertNotIn("Skipping upload for 55c609fe8808aa5308134cb5989d23d3caffccf2", out)
                self.assertNotIn("Skipping upload for 1744785cb24e3bdca70e27041dc5abd20476f947", out)
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:55c609fe8808aa5308134cb5989d23d3caffccf2")
                self.assertRegex(out, r"Uploading package 'lib/1.0@user/testing#.*:1744785cb24e3bdca70e27041dc5abd20476f947")
            else:
                self.assertNotIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", out)
                self.assertNotIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", out)
                self.assertIn("Uploading package 1/2", out)
                self.assertIn("Uploading package 2/2", out)
            self.assertIn("HALLO", out)

    def test_upload_partial_reference(self):
        ts = TestServer(users={"user": "password"},
                        write_permissions=[("lib/1.0@*/*", "user")])
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_REFERENCE": "lib/1.0@",
                                 }):

            mp = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"])
            mp.add_common_builds(shared_option_name=False)
            mp.run()
            out = mp.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading packages for 'lib/1.0#", out)
            else:
                self.assertIn("Uploading packages for 'lib/1.0@'", out)
            self.assertIn("lib/1.0: WARN: HALLO", out)

    def test_forced_upload(self):
        NO_SETTINGS_PACKAGE_ID ="da39a3ee5e6b4b0d3255bfef95601890afd80709" if CONAN_V2 else "5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9"
        conanfile = textwrap.dedent("""
                from conan import ConanFile
                class Pkg(ConanFile):

                    def configure(self):
                        self.output.warning("Mens sana in corpore sano")
        """)
        ts = TestServer(users={"foo": "password"})
        tc = TestClient(servers={"foo_server": ts}, users={"foo_server": [("foo", "password")]})

        tc.save({"conanfile.py": conanfile})
        tc.run(f"create . { pos_args('lib/1.0@foo/stable') }")
        tc.run(f"upload lib/1.0@foo/stable {'' if CONAN_V2 else '--all'} -r foo_server")
        if CONAN_V2:
            from conans.model.recipe_ref import RecipeReference
            rref = RecipeReference.loads("lib/1.0@foo/stable")
            rref.revision = ts.server_store.get_last_revision(rref).revision
            pref = PackageReference(rref, NO_SETTINGS_PACKAGE_ID)
            pref = ts.server_store.get_last_package_revision(pref)
            path = ts.server_store.package(pref)
        else:
            pref = PackageReference.loads("lib/1.0@foo/stable#{}:{}".format(0, NO_SETTINGS_PACKAGE_ID))
            path = os.path.join(ts.server_store.package_revisions_root(pref), "0")
        manifest = FileTreeManifest.load(path)
        manifest.time += 1000
        manifest.save(path)

        tc.save({"conanfile.py": conanfile.replace("warning", "info")})
        tc.run(f"create . { pos_args('lib/1.0@foo/stable')}")

        # Force is True, package must be uploaded all times
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "foo",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "foo",
                                "CONAN_UPLOAD_FORCE": "True"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"])
            mulitpackager.add_common_builds(reference="lib/1.0@foo/stable",
                                            shared_option_name=False)
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()
            if CONAN_V2:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable#", out)
                # TODO how to check that in conan2 ?
                self.assertNotIn("Recipe is up to date, upload skipped", out)
                self.assertNotIn("Package is up to date, upload skipped", out)
            else:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable'", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)
                self.assertNotIn("Package is up to date, upload skipped", out)

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "foo",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "foo",
                                "CONAN_UPLOAD_FORCE": "FALSE"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"],
                                                      upload_force=True)
            mulitpackager.add_common_builds(reference="lib/1.0@foo/stable",
                                            shared_option_name=False)

            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable#", out)
                # TODO how to handle in conan2?
                self.assertNotIn("Package is up to date, upload skipped", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)
            else:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable'", out)
                self.assertNotIn("Package is up to date, upload skipped", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)

        # Force is False. Must not upload any package
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "foo",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "foo",
                                "CONAN_UPLOAD_FORCE": "FALSE"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"], archs=["x86"],
                                                      upload_force=False)
            mulitpackager.add_common_builds(reference="lib/1.0@foo/stable",
                                            shared_option_name=False)

            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable#", out)
                # TODO how to handle in conan2?
                self.assertNotIn("Package is up to date, upload skipped", out)
                self.assertNotIn("Recipe is up to date, upload skipped", out)
            else:
                self.assertIn("Uploading packages for 'lib/1.0@foo/stable'", out)
                self.assertIn("Recipe is up to date, upload skipped", out)
                self.assertIn("Package is up to date, upload skipped", out)


class UploadDependenciesTest(unittest.TestCase):

    conanfile_bar = """from conan import ConanFile
class Pkg(ConanFile):
    name = "bar"
    version = "0.1.0"

    def build(self):
        pass
    """

    conanfile_foo = """from conan import ConanFile
class Pkg(ConanFile):
    name = "foo"
    version = "1.0.0"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def build(self):
        pass
    """

    conanfile = """from conan import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "2.0"
    requires = "bar/0.1.0@foo/stable", "foo/1.0.0@bar/testing"

    def build(self):
        self.output.warning("BUILDING")
"""

    def setUp(self):
        self._ci_manager = MockCIManager()
        self._server = TestServer(users={"user": "password"},
                                  write_permissions=[("bar/*@foo/stable", "user"),
                                                     ("foo/*@bar/testing", "user"),
                                                     ("foobar/2.0@user/testing", "user")])
        self._client = TestClient(servers={"default": self._server},
                                 users={"default": [("user", "password")]})
        self._client.save({"conanfile_bar.py": self.conanfile_bar})
        self._client.run(f"export conanfile_bar.py { pos_args('foo/stable') }")
        self._client.save({"conanfile_foo.py": self.conanfile_foo})
        self._client.run(f"export conanfile_foo.py { pos_args('bar/testing') }")
        self._client.save({"conanfile.py": self.conanfile})

    def test_upload_all_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading package 'foobar/2.0@user/testing#", out)
                self.assertIn("Uploading recipe 'foobar/2.0@user/testing#", out)

                self.assertIn("Uploading package 'bar/0.1.0@foo/stable#", out)
                self.assertIn("Uploading recipe 'bar/0.1.0@foo/stable#", out)

                self.assertIn("Uploading package 'foo/1.0.0@bar/testing#", out)
                self.assertIn("Uploading recipe 'foo/1.0.0@bar/testing#", out)
            else:
                self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", out)
                self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", out)
                self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", out)

                self.assertIn("Uploading packages for 'bar/0.1.0@foo/stable'", out)
                self.assertIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", out)
                self.assertIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", out)

                self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", out)
                self.assertIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", out)
                self.assertIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", out)

    def test_invalid_upload_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all,bar/0.1.0@foo/stable"}):
            with self.assertRaises(Exception) as context:
                get_patched_multipackager(self._client, exclude_vcvars_precommand=True)
            self.assertIn("Upload dependencies only accepts or 'all' or package references. Do not mix both!", str(context.exception))


    def test_upload_specific_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "foo/1.0.0@bar/testing"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading package 'foobar/2.0@user/testing#", out)
                self.assertIn("Uploading recipe 'foobar/2.0@user/testing#", out)

                self.assertNotIn("Uploading package 'bar/0.1.0@foo/stable#", out)
                self.assertNotIn("Uploading recipe 'bar/0.1.0@foo/stable#", out)

                self.assertIn("Uploading package 'foo/1.0.0@bar/testing#", out)
                self.assertIn("Uploading recipe 'foo/1.0.0@bar/testing#", out)
            else:
                self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
                self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", self._client.out)
                self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", self._client.out)

                self.assertNotIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
                self.assertNotIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", self._client.out)
                self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", self._client.out)

                self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
                self.assertIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", self._client.out)
                self.assertIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", self._client.out)

    def test_upload_regex_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "foo/*"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)

            mulitpackager.add({}, {})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if CONAN_V2:
                self.assertIn("Uploading package 'foobar/2.0@user/testing#", out)
                self.assertIn("Uploading recipe 'foobar/2.0@user/testing#", out)

                self.assertNotIn("Uploading package 'bar/0.1.0@foo/stable#", out)
                self.assertNotIn("Uploading recipe 'bar/0.1.0@foo/stable#", out)

                self.assertNotIn("Uploading package 'foo/1.0.0@bar/testing#", out)
                self.assertNotIn("Uploading recipe 'foo/1.0.0@bar/testing#", out)
            else:
                self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", out)
                self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", out)
                self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", out)

                self.assertNotIn("Uploading packages for 'bar/0.1.0@foo/stable'", out)
                self.assertNotIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", out)
                self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", out)

                self.assertNotIn("Uploading packages for 'foo/1.0.0@bar/testing'", out)
                self.assertNotIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", out)
                self.assertNotIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", out)
