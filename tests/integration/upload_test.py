from cpt.packager import ConanMultiPackager
from tests.integration.base import BaseTest
from tests.unit.utils import MockCIManager
from cpt._compat import CONAN_V2, ConanException, add_remote, environment_append

class UploadTest(BaseTest):

    conanfile = """from conan import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

"""
    ci_manager = MockCIManager()

    def test_no_upload_remote(self):

        self.save_conanfile(self.conanfile)
        mp = ConanMultiPackager(username="lasote", out=self.output.write)
        mp.add({}, {}, {})
        mp.run()
        self.assertIn("Upload skipped, not upload remote available", self.output)

    def test_no_credentials(self):
        self.save_conanfile(self.conanfile)
        mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                ci_manager=self.ci_manager,
                                upload=("https://uilianr.jfrog.io/artifactory/api/conan/public-conan",
                                        True, "my_upload_remote"))
        mp.add({}, {}, {})
        mp.run()
        self.assertIn("Upload skipped, credentials for remote 'my_upload_remote' "
                      "not available", self.output)
        self.assertNotIn("Uploading packages", self.output)

    def test_no_credentials_but_skip(self):
        with environment_append({"CONAN_NON_INTERACTIVE": "1"}):
            self.save_conanfile(self.conanfile)
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    ci_manager=self.ci_manager,
                                    upload=("https://uilianr.jfrog.io/artifactory/api/conan/public-conan",
                                            True, "my_upload_remote"),
                                    skip_check_credentials=True)
            mp.add({}, {}, {})
            if CONAN_V2:
                with self.assertRaisesRegex(ConanException, "doesn't seem like a valid"):
                    mp.run()
            else:
                with self.assertRaisesRegex(ConanException, "Errors uploading some packages"):
                    mp.run()
                
            self.assertIn("Uploading packages for", self.output)
            self.assertIn("Credentials not specified but 'skip_check_credentials' activated",
                          self.output)

    def test_no_credentials_only_url(self):
        self.save_conanfile(self.conanfile)
        mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                ci_manager=self.ci_manager,
                                upload="https://uilianr.jfrog.io/artifactory/api/conan/public-conan")
        mp.add({}, {}, {})
        mp.run()
        self.assertIn("Upload skipped, credentials for remote 'upload_repo' "
                      "not available", self.output)
        self.assertNotIn("Uploading packages", self.output)

    def test_no_credentials_wrong_userpass(self):
        self.save_conanfile(self.conanfile)
        with environment_append({"CONAN_PASSWORD": "mypass"}):
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    ci_manager=self.ci_manager,
                                    upload="https://uilianr.jfrog.io/artifactory/api/conan/public-conan")
            with self.assertRaises(ConanException) as context:
                mp.run()
                self.assertTrue(any("Wrong user or password" in context.exception,
                                    "blocked due to recurrent login failures"  in context.exception))

    def test_no_credentials_only_url_skip_check(self):
        self.save_conanfile(self.conanfile)
        with environment_append({"CONAN_PASSWORD": "mypass",
                                       "CONAN_UPLOAD_ONLY_WHEN_STABLE": "1"}):
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    channel="my_channel",
                                    ci_manager=self.ci_manager,
                                    upload="https://uilianr.jfrog.io/artifactory/api/conan/public-conan",)
            mp.add({}, {}, {})
            mp.run()
            self.assertIn("Skipping upload, not stable channel", self.output)

    def test_upload_only_stable(self):
        self.save_conanfile(self.conanfile)
        with environment_append({"CONAN_PASSWORD": "mypass",
                                       "CONAN_SKIP_CHECK_CREDENTIALS": "1"}):
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    ci_manager=self.ci_manager,
                                    upload="https://uilianr.jfrog.io/artifactory/api/conan/public-conan")
            mp.run()  # No builds to upload so no raises
            self.assertNotIn("Wrong user or password", self.output)

    def test_existing_upload_repo(self):
        add_remote(self.api, "my_upload_repo", "https://uilianr.jfrog.io/artifactory/api/conan/public-conan", True)

        self.save_conanfile(self.conanfile)
        with environment_append({"CONAN_PASSWORD": "mypass"}):
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    ci_manager=self.ci_manager,
                                    upload=["https://uilianr.jfrog.io/artifactory/api/conan/public-conan",
                                            False, "othername"])
            mp.add({}, {}, {})
            with self.assertRaises(ConanException) as context:
                mp.run()
                self.assertTrue(any("Wrong user or password" in context.exception,
                                    "blocked due to recurrent login failures"  in context.exception))
            # The upload repo is kept because there is already an url
            # FIXME: Probaby we should rename if name is different (Conan 1.3)
            self.assertIn("Remote for URL 'https://uilianr.jfrog.io/artifactory/api/conan/public-conan' "
                          "already exist, keeping the current remote and its name", self.output)

    def test_existing_upload_repo_by_name(self):
        add_remote(self.api, "upload_repo", "https://foobar.jfrog.io/artifactory/api/conan/public-conan", True)

        self.save_conanfile(self.conanfile)
        with environment_append({"CONAN_PASSWORD": "mypass",
                                       "CONAN_UPLOAD": "https://uilianr.jfrog.io/artifactory/api/conan/public-conan"
                                      }):
            mp = ConanMultiPackager(username="lasote", out=self.output.write,
                                    ci_manager=self.ci_manager)
            mp.add({}, {}, {})
            with self.assertRaises(ConanException) as context:
                mp.run()
                self.assertTrue(any("Wrong user or password" in context.exception,
                                    "blocked due to recurrent login failures"  in context.exception))
            self.assertNotIn("already exist, keeping the current remote and its name", self.output)
            if CONAN_V2:
                repo = self.api.remotes.get("upload_repo")
            else:
                repo = self.api.get_remote_by_name("upload_repo")
            self.assertEqual(repo.url, "https://uilianr.jfrog.io/artifactory/api/conan/public-conan")
