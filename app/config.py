import os
import sys

TENANT_NAME = None
CLIENT_ID = None
CLIENT_SECRET = None
APP_OBJECT_ID = None
APP_NAME = None


def print_and_quit(variable):
    print("Please set the environment variable {}.".format(variable))
    sys.exit(1)


try:
    TENANT_NAME = os.environ["TENANT_NAME"]
    CLIENT_ID = os.environ["CLIENT_ID"]
    CLIENT_SECRET = os.environ["CLIENT_SECRET"]
    APP_OBJECT_ID = os.environ["APP_OBJECT_ID"]
    APP_NAME = os.environ["APP_NAME"]

except KeyError as k:
    print_and_quit(k.args[0])
