# -*- coding: utf-8 -*-
"""fetcher.py -- GitHub API and file fetching logic"""

import requests
import base64
from urllib.parse import urlparse
from pathlib import PurePosixPath
import concurrent.futures

def parse_github_url(url):
    parsed_url = urlparse(url)
    segments = parsed_url.path.strip("/").split("/")
    if len(segments) < 2:
        raise ValueError("Invalid GitHub URL provided!")
    owner, repo = segments[0], segments[1]
    branch = 'main'
    if 'tree' in segments:
        idx = segments.index('tree')
        if idx + 1 < len(segments):
            branch = segments[idx + 1]
    return owner, repo, branch

def fetch_tree(owner, repo, branch, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-repo-parser"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        # branch may be a sha, try using refs/heads/<branch>
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/refs/heads/{branch}?recursive=1"
        resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()['tree']

def fetch_content(owner, repo, path, branch, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-repo-parser"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, params={'ref': branch})
    resp.raise_for_status()
    return resp.json()

def decode_file_content(file_info):
    if file_info.get('encoding') == 'base64':
        return base64.b64decode(file_info['content']).decode('utf-8')
    return file_info.get('content', '')

def is_public_repo(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"User-Agent": "github-repo-parser"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return not resp.json().get('private', False)
    return False

def fetch_raw_content(owner, repo, branch, path):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def fetch_file_content(args):
    owner, repo, path, branch, token, is_public = args
    try:
        if is_public:
            return path, fetch_raw_content(owner, repo, branch, path)
        else:
            file_info = fetch_content(owner, repo, path, branch, token)
            return path, decode_file_content(file_info)
    except Exception as e:
        return path, f"# ERROR: Could not fetch file: {e}"

def fetch_all_contents(owner, repo, included_files, branch, token, is_public, max_workers=8):
    args_list = [(owner, repo, path, branch, token, is_public) for path in included_files if path != 'README.md']
    contents = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for path, content in executor.map(fetch_file_content, args_list):
            contents[path] = content
    return contents

def normalize_path(path):
    return str(PurePosixPath(path))
