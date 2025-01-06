from cpt._compat import list_remotes, remove_remote, add_remote
from cpt.printer import Printer
from cpt.remotes import RemotesManager
from tests.integration.base import BaseTest


class RemotesTest(BaseTest):

    def test_duplicated_remotes_with_different_url(self):
        remove_remote(self.api, "conancenter")
        add_remote(self.api, "upload_repo", "url_different", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")


        remotes = list_remotes(self.api)
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        manager.add_remotes_to_conan()

        self.assertEqual(len(list_remotes(self.api)), 1)

        manager.add_remotes_to_conan()

        self.assertEqual(len(list_remotes(self.api)), 1)

    def test_duplicated_remotes_with_same_url(self):
        remove_remote(self.api, "conancenter")
        add_remote(self.api, "upload_repo", "url1", True)

        manager = RemotesManager(self.api, Printer(), remotes_input="url1@True@upload_repo",
                                 upload_input="url1@True@upload_repo")

        remotes = list_remotes(self.api)
        self.assertIsNotNone(manager._get_remote_by_name(remotes, "upload_repo"))

        manager.add_remotes_to_conan()
        self.assertEqual(len(list_remotes(self.api)), 1)
