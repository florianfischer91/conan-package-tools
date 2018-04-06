import re
import os
import subprocess


def is_travis():
    return os.getenv("TRAVIS", False)


def is_appveyor():
    return os.getenv("APPVEYOR", False)


def is_bamboo():
    return os.getenv("bamboo_buildNumber", False)


def is_jenkins():
    return os.getenv("JENKINS_URL", False)


def is_gitlab():
    return os.getenv("GITLAB_CI", False)


def is_circle_ci():
    return os.getenv("CIRCLECI", False)


class CIManager(object):

    def __init__(self):

        self.manager = None
        if is_travis():
            self.manager = TravisManager()
        elif is_appveyor():
            self.manager = AppveyorManager()
        elif is_bamboo():
            self.manager = BambooManager()
        elif is_circle_ci():
            self.manager = CircleCiManager()
        elif is_gitlab():
            self.manager = GitlabManager()
        elif is_jenkins():
            self.manager = JenkinsManager()
        else:
            self.manager = GenericManager()

    def get_commit_build_policy(self):
        pattern = "^.*\[build=(\w*)\].*$"
        prog = re.compile(pattern)
        msg = self.get_commit_msg()
        matches = prog.match(msg)
        if matches:
            build_policy = matches.groups()[0]
            if build_policy not in ("never", "outdated", "missing"):
                raise Exception("Invalid build policy, valid values: never, outdated, missing")
            return build_policy
        return None

    def skip_builds(self):
        pattern = "^.*\[skip ci\].*$"
        prog = re.compile(pattern)
        msg = self.get_commit_msg()
        return prog.match(msg)

    def get_branch(self):
        return self.manager.get_branch()

    def get_commit_msg(self):
        return self.manager.get_commit_msg()

    def is_pull_request(self):
        return self.manager.is_pull_request()


class GenericManager(object):

    def get_commit_msg(self):
        try:
            msg = subprocess.check_output("git log -1 --format=%s%n%b", shell=True).decode().strip()
            return msg
        except Exception:
            pass

    def get_branch(self):
        try:
            msg = subprocess.check_output("git branch | grep \*", shell=True).decode().strip()
            if " (HEAD detached" not in msg:
                return msg
            return None
        except Exception:
            pass

        return None

    def is_pull_request(self):
        return None


class TravisManager(GenericManager):

    def get_commit_msg(self):
        return os.getenv("TRAVIS_COMMIT_MESSAGE", None)

    def get_branch(self):
        return os.getenv("TRAVIS_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("TRAVIS_PULL_REQUEST", "false") != "false"


class AppveyorManager(GenericManager):

    def get_commit_msg(self):
        commit = os.getenv("APPVEYOR_REPO_COMMIT_MESSAGE", None)
        if commit:
            extended = os.getenv("APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED", None)
            if extended:
                return commit + " " + extended
        return commit

    def get_branch(self):
        if self.is_pull_request():
            return None

        return os.getenv("APPVEYOR_REPO_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("APPVEYOR_PULL_REQUEST_NUMBER", None)


class BambooManager(GenericManager):

    def get_branch(self):
        return os.getenv("bamboo_planRepository_branch", None)


class CircleCiManager(GenericManager):

    def get_branch(self):
        return os.getenv("CIRCLE_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("CIRCLE_PULL_REQUEST", None)


class GitlabManager(GenericManager):

    def get_branch(self):
        return os.getenv("CI_BUILD_REF_NAME", None)


class JenkinsManager(GenericManager):

    def get_branch(self):
        return os.getenv("BRANCH_NAME", None)
