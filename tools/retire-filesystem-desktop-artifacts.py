#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Withdraw archived APT snapshots configured to include the retired helper."""
import base64
import json
import os
import re
import urllib.request
from urllib.error import HTTPError

repository = os.environ['GITHUB_REPOSITORY']
assert repository == 'Infiltrator-Projects/Infiltrator-Repository'
token = os.environ['GH_TOKEN']
current_run = int(os.environ['GITHUB_RUN_ID'])
# The helper first became a published binary at this time.
first_published = '2026-10-03T09:00:11Z'
retired_package = '^infiltrator-filesystem-support-udisks$'

def api(path, method='GET'):
    assert path.startswith(f'repos/{repository}/')
    request = urllib.request.Request('https://api.github.com/' + path, method=method,
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as error:
        if method == 'DELETE' and error.code == 404:
            return None  # Another publication already removed this exact artifact.
        raise

artifacts = []
page = 1
while True:
    batch = api(f'repos/{repository}/actions/artifacts?per_page=100&page={page}')['artifacts']
    artifacts.extend(batch)
    if len(batch) < 100:
        break
    page += 1

configured = {}
deleted = 0
for artifact in artifacts:
    if artifact['expired'] or artifact['created_at'] < first_published:
        continue
    if not re.fullmatch(r'github-pages(?:-\d+)?', artifact['name']):
        continue
    run = artifact.get('workflow_run') or {}
    if run.get('id') == current_run:
        continue
    sha = run.get('head_sha', '')
    assert re.fullmatch(r'[0-9a-f]{40}', sha), 'Missing snapshot source identity'
    if sha not in configured:
        source = api(f'repos/{repository}/contents/catalogue/apps-source.json?ref={sha}')
        assert source['encoding'] == 'base64'
        catalogue = json.loads(base64.b64decode(source['content']))
        entry = next((item for item in catalogue if item['id'] == 'filesystem-support'), {})
        configured[sha] = any(item.get('expected_package_regex') == retired_package
                              for item in entry.get('supplemental_packages', []))
    # The publisher validates every configured supplemental package before
    # uploading a Pages snapshot. This exact source entry identifies snapshots
    # that carry the retired binary; other snapshots/artifacts remain intact.
    if configured[sha]:
        api(f"repos/{repository}/actions/artifacts/{artifact['id']}", 'DELETE')
        deleted += 1
        print(f"Deleted retired-package APT snapshot {artifact['id']} ({sha})", flush=True)
print(f'Retired-package APT snapshot cleanup complete: {deleted} deleted', flush=True)
