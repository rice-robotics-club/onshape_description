#!/usr/bin/env python3
"""Register an Onshape webhook that re-exports this repository whenever a version is created.

Used by .github/workflows/register-webhook.yml. The webhook targets the club's relay
(rice-robotics-club/onshape_webhook, URL in $RELAY_URL) with ``?repo=<this repository>``; the relay turns each
``onshape.model.lifecycle.createversion`` event into a repository_dispatch that runs Update URDF.

Onshape doesn't de-duplicate webhooks, so only run this once per repository (re-running creates a
second webhook and every version would be exported twice).
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import commentjson


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def main() -> None:
    relay = os.environ.get("RELAY_URL", "").rstrip("/")
    repo = os.environ["REPOSITORY_NAME"]
    if not relay.startswith("https://"):
        fail("Set the ONSHAPE_WEBHOOK_RELAY_URL organization variable to the relay's https:// URL.")

    with open("config.json") as stream:
        config = commentjson.load(stream)
    document_id = config.get("document_id")
    if config.get("url"):
        match = re.search(r"/documents/([0-9a-f]{24})/", config["url"])
        document_id = match.group(1) if match else None
    if not document_id or not re.fullmatch(r"[0-9a-f]{24}", document_id):
        fail("config.json has no valid document_id (or url).")

    body = {
        "events": ["onshape.model.lifecycle.createversion"],
        "documentId": document_id,
        "url": f"{relay}/onshape?{urllib.parse.urlencode({'repo': repo})}",
        "options": {"collapseEvents": False},
        "isTransient": False,  # don't let Onshape clean it up after a period of inactivity
        "description": f"Update URDF in {os.environ.get('GITHUB_REPOSITORY', repo)}",
    }
    api = os.environ.get("ONSHAPE_API", "https://cad.onshape.com").rstrip("/")
    credentials = f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}"
    request = urllib.request.Request(
        f"{api}/api/v6/webhooks",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            webhook = json.load(response)
    except urllib.error.HTTPError as error:
        fail(f"Onshape rejected the webhook: {error.code} {error.read().decode(errors='replace')}")

    print(f"Registered webhook {webhook.get('id')} for document {document_id} -> {body['url']}")
    print("Onshape now sends a webhook.register check to the relay; if the relay doesn't answer 200")
    print("(e.g. wrong signature key), Onshape cancels the registration. Check the relay's logs.")


if __name__ == "__main__":
    main()
