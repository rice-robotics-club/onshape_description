#!/usr/bin/env python3
"""Pin config.json to the Onshape version sent by the webhook relay (repository_dispatch).

Used by .github/workflows/update-urdf.yml. Reads the dispatch payload from $PAYLOAD
(``{"documentId", "versionId", ...}``), checks that it is for this repository's Onshape
document, and rewrites config.json so onshape-to-robot exports that exact version
(``version_id`` instead of ``workspace_id``, or ``/v/<version>/`` in ``url``). The edited
config.json is only used for this run; the workflow never commits it.

It then looks up the version's name through the Onshape API and writes two step outputs:
``commit_message`` and ``tag`` (``onshape-<version name>``).
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import urllib.request

import commentjson  # installed with onshape-to-robot; config.json may contain comments

ONSHAPE_ID = re.compile(r"^[0-9a-f]{24}$")
CONFIG = "config.json"


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def version_name(document_id: str, version_id: str) -> str | None:
    api = os.environ.get("ONSHAPE_API", "https://cad.onshape.com").rstrip("/")
    credentials = f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}"
    request = urllib.request.Request(
        f"{api}/api/v6/documents/d/{document_id}/versions/{version_id}",
        headers={
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response).get("name")
    except Exception as error:  # the export itself doesn't depend on the name
        print(f"::warning::Couldn't fetch the Onshape version name ({error}); using its id instead.")
        return None


def main() -> None:
    payload = json.loads(os.environ.get("PAYLOAD") or "{}")
    document_id = payload.get("documentId", "")
    version_id = payload.get("versionId", "")
    if not ONSHAPE_ID.match(document_id) or not ONSHAPE_ID.match(version_id):
        fail(f"Malformed dispatch payload: {payload}")

    with open(CONFIG) as stream:
        config = commentjson.load(stream)

    if config.get("url"):
        match = re.match(r"^(https://[^/]+/documents/([0-9a-f]{24}))/[wv]/[0-9a-f]{24}(/e/.*)$", config["url"])
        if not match:
            fail(f"Can't pin a version in config.json url: {config['url']}")
        configured_document = match.group(2)
        config["url"] = f"{match.group(1)}/v/{version_id}{match.group(3)}"
    else:
        configured_document = config.get("document_id")
        config.pop("workspace_id", None)  # onshape-to-robot rejects workspace_id + version_id
        config["version_id"] = version_id

    if configured_document != document_id:
        fail(
            f"Webhook is for Onshape document {document_id}, but config.json exports"
            f" {configured_document}; re-register the webhook for this repository."
        )

    with open(CONFIG, "w") as stream:
        json.dump(config, stream, indent=2)

    name = version_name(document_id, version_id) or version_id
    name = " ".join(name.split())  # one line, for the commit message and step output
    tag = "onshape-" + (re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or version_id)
    if subprocess.run(["git", "check-ref-format", f"refs/tags/{tag}"]).returncode != 0:
        tag = f"onshape-{version_id}"
    message = f"Update from Onshape version {name}"
    print(f"Exporting Onshape version '{name}' ({version_id})")

    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"commit_message={message}\n")
        output.write(f"tag={tag}\n")


if __name__ == "__main__":
    main()
