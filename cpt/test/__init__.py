import os

# we don't want to get errors when running pip during tests
os.environ["PIP_REQUIRE_VIRTUALENV"] = "false"
