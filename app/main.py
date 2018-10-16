import datetime
import json
import os
import uuid
from pprint import pprint
from ssl import create_default_context
from urllib import parse

import adal
import dateutil
import requests
from flask import Flask, Response, redirect, render_template, request, session, url_for

import config

app = Flask(__name__)
app.secret_key = os.urandom(16)


@app.route("/")
def index():
    if session.get("access_token") is not None:
        role_assignment = session.get("role_assignment", get_user_role_assignment())
        if role_assignment is None or role_assignment == []:
            return render_template("unauthorized.html")
        session["role_assignment"] = role_assignment

        return render_template(
            "index.html",
            logged_in=True,
            user_name=session["given_name"],
            roles=session["role_assignment"],
        )

    return render_template("index.html")


def get_user_role_assignment():
    if session.get("access_token") is None:
        return None

    endpoint = "https://graph.microsoft.com/beta/me/appRoleAssignments/"
    headers = {
        "Authorization": session["access_token"],
        "User-Agent": config.APP_NAME,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "client-request-id": str(uuid.uuid4()),
    }

    r = requests.get(url=endpoint, headers=headers, stream=False).json()

    print("User role assignment: ")
    print(json.dumps(r))

    roles_for_this_app = []
    for role in r["value"]:
        if role["resourceDisplayName"] == config.APP_NAME:
            roles_for_this_app.append(role["appRoleId"])

    app_roles = get_app_roles()
    app_role_id_map = {}
    for role in app_roles:
        app_role_id_map[role["id"]] = {
            "internal_role_name": role["value"],
            "role_display_name": role["displayName"],
            "role_description": role["description"],
        }

    effective_role_dicts = []
    for role_id in roles_for_this_app:
        effective_role_dicts.append(app_role_id_map[role_id])

    return effective_role_dicts


def get_app_roles():
    if session.get("access_token") is None:
        return None

    endpoint = "https://graph.microsoft.com/beta/applications/{}".format(
        config.APP_OBJECT_ID
    )
    headers = {
        "Authorization": session["access_token"],
        "User-Agent": config.APP_NAME,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "client-request-id": str(uuid.uuid4()),
    }

    r = requests.get(url=endpoint, headers=headers, stream=False).json()

    print("App roles: ")
    print(json.dumps(r))

    return r["appRoles"]


@app.route("/login")
def login():
    auth_state = str(uuid.uuid4())
    session["state"] = auth_state
    authorization_url = (
        "https://login.microsoftonline.com/{}/oauth2/authorize?"
        + "response_type=code&client_id={}&redirect_uri={}&"
        + "state={}&resource={}"
    ).format(
        config.TENANT_NAME,
        config.CLIENT_ID,
        url_for("get_a_token", _external=True, _scheme="http"),
        auth_state,
        "https://graph.microsoft.com",
    )

    resp = Response(status=307)
    resp.headers["location"] = authorization_url
    return resp


@app.route("/logout")
def logout():
    session.pop("access_token")
    resp = redirect(
        location="https://login.microsoftonline.com/{}/oauth2/logout?post_logout_redirect_uri={}".format(
            config.TENANT_NAME,
            parse.quote(url_for("index", _external=True, _scheme="http")),
        ),
        code=307,
    )
    return resp


@app.route("/get_a_token")
def get_a_token():
    code = request.args["code"]
    state = request.args["state"]
    if state != session["state"]:
        raise ValueError("State does not match across requests.")
    auth_context = adal.AuthenticationContext(
        "https://login.microsoftonline.com/{}".format(config.TENANT_NAME)
    )
    token_response = auth_context.acquire_token_with_authorization_code(
        code,
        url_for("get_a_token", _external=True, _scheme="http"),
        "https://graph.microsoft.com",
        config.CLIENT_ID,
        config.CLIENT_SECRET,
    )
    session["access_token"] = token_response["accessToken"]
    session["user_id"] = token_response["userId"]
    session["given_name"] = token_response["givenName"]

    return redirect(url_for("index"))
