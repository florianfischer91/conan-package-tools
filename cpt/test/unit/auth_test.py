import unittest

from cpt.test.utils.tools import TestBufferConanOutput
from cpt.auth import AuthManager
from cpt.printer import Printer
from cpt.test.unit.packager_test import MockConanAPI
from cpt._compat import environment_append

class AuthTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()
        self.output = TestBufferConanOutput()
        self.printer = Printer(self.output.write)

    def no_credentials_test(self):
        manager = AuthManager(self.conan_api, self.printer)
        user, password = manager.get_user_password()
        self.assertEqual(user, None)
        self.assertEqual(password, None)

    def test_plain_credentials(self):

        # Without default
        manager = AuthManager(self.conan_api, self.printer, login_input="myuser",
                              passwords_input="mypassword")

        user, password = manager.get_user_password("any")
        self.assertEqual(user, "myuser")
        self.assertEqual(password, "mypassword")

        user, password = manager.get_user_password(None)
        self.assertEqual(user, "myuser")
        self.assertEqual(password, "mypassword")

        # Only password is discarded
        manager = AuthManager(self.conan_api, self.printer, passwords_input="mypassword")
        user, password = manager.get_user_password()
        self.assertEqual(user, None)
        self.assertEqual(password, None)

        # With default
        manager = AuthManager(self.conan_api, self.printer,
                              passwords_input="mypassword",
                              default_username="myuser")

        user, password = manager.get_user_password("any")
        self.assertEqual(user, "myuser")
        self.assertEqual(password, "mypassword")

    def plain_from_env_test(self):
        with environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer)
            user, password = manager.get_user_password()
            self.assertEqual(user, "myuser")
            self.assertEqual(password, "mypass")

    def plain_multiple_from_env_test(self):
        # Bad mix
        with environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            with self.assertRaisesRegex(Exception, "Password for remote 'R1' not specified"):
                AuthManager(self.conan_api, self.printer)

        with environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD_R1": "mypass",
                                       "CONAN_LOGIN_USERNAME_R_OTHER": "myuser2",
                                       "CONAN_PASSWORD_R_OTHER": "mypass2"}):
            manager = AuthManager(self.conan_api, self.printer)
            user, password = manager.get_user_password("r1")
            self.assertEqual(user, "myuser")
            self.assertEqual(password, "mypass")

            user, password = manager.get_user_password("r_other")
            self.assertEqual(user, "myuser2")
            self.assertEqual(password, "mypass2")

        # Miss password
        with environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD_R2": "mypass"}):
            with self.assertRaisesRegex(Exception, "Password for remote 'R1' not specified"):
                AuthManager(self.conan_api, self.printer)

    def plain_from_env_priority_test(self):
        with environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer, login_input="otheruser",
                                  passwords_input="otherpass")
            user, password = manager.get_user_password()
            self.assertEqual(user, "otheruser")
            self.assertEqual(password, "otherpass")

    def plain_from_env_priority_mix_test(self):
        with environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer, login_input="otheruser")
            user, password = manager.get_user_password()
            self.assertEqual(user, "otheruser")
            self.assertEqual(password, "mypass")

    def test_dict_credentials(self):
        users = {"remote1": "my_user", "my_artifactory": "other_user"}
        passwords = {"remote1": "my_pass", "my_artifactory": "my_pass2"}
        manager = AuthManager(self.conan_api, self.printer, login_input=users,
                              passwords_input=passwords,
                              default_username=None)

        with self.assertRaisesRegex(Exception, "User and password for remote "
                                                "'not_exist' not specified"):
            manager.get_user_password("not_exist")

        user, password = manager.get_user_password("my_artifactory")
        self.assertEqual(user, "other_user")
        self.assertEqual(password, "my_pass2")

        user, password = manager.get_user_password("remote1")
        self.assertEqual(user, "my_user")
        self.assertEqual(password, "my_pass")

        # Mix them
        with self.assertRaisesRegex(Exception, "Specify a dict for 'login_username'"):
            AuthManager(self.conan_api, self.printer, passwords_input=passwords, default_username="peter")

    def test_env_vars_output(self):
        users = {"remote1": "my_user", "my_artifactory": "other_user"}
        passwords = {"remote1": "my_pass", "my_artifactory": "my_pass2"}
        manager = AuthManager(self.conan_api, self.printer, login_input=users,
                              passwords_input=passwords)
        expected = {'CONAN_PASSWORD_REMOTE1': 'my_pass',
                    'CONAN_LOGIN_USERNAME_REMOTE1': 'my_user',
                    'CONAN_PASSWORD_MY_ARTIFACTORY': 'my_pass2',
                    'CONAN_LOGIN_USERNAME_MY_ARTIFACTORY': 'other_user'}
        self.assertEqual(manager.env_vars(), expected)

        with environment_append(expected):
            manager = AuthManager(self.conan_api, self.printer)
            self.assertEqual(manager.env_vars(), expected)

        manager = AuthManager(self.conan_api, self.printer, login_input="myuser",
                              passwords_input="mypassword")
        expected = {'CONAN_PASSWORD': 'mypassword',
                    'CONAN_LOGIN_USERNAME': 'myuser'}

        self.assertEqual(manager.env_vars(), expected)
