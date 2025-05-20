# -*- coding: utf-8 -*-
"""GitHub Repo Parser"""

import requests
import base64
import nbformat
from nbconvert import PythonExporter
import os
import getpass
import re
import fnmatch
import yaml
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime
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

def ipynb_to_py(nb_string):
    notebook = nbformat.reads(nb_string, as_version=4)
    code, _ = PythonExporter().from_notebook_node(notebook)
    code = clean_converted_code(code)
    return code

def clean_converted_code(code: str) -> str:
    lines = code.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('get_ipython()'):
            continue
        if stripped.startswith('#!') or stripped.startswith('# coding:'):
            continue
        if stripped.startswith('# #'):
            continue
        if re.match(r'# In\[.*\]:?', stripped):
            continue
        if stripped == '':
            if cleaned_lines and cleaned_lines[-1].strip() == '':
                continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip() + '\n'

def normalize_path(path):
    return str(PurePosixPath(path))

def match_any(path, patterns):
    # patterns: list of globs, file/dir names, or dir globs ending with /
    if not patterns:
        return False
    norm_path = normalize_path(path)
    for pat in patterns:
        pat = pat.strip()
        pat_norm = normalize_path(pat)
        if pat.endswith('/'):
            if norm_path.startswith(pat_norm):
                return True
        elif '*' in pat or '?' in pat or '[' in pat:
            if fnmatch.fnmatch(norm_path, pat_norm):
                return True
        else:
            if norm_path == pat_norm:
                return True
    return False

def should_include_file(path, config):
    include = [normalize_path(p) for p in config.get('include', [])]
    exclude = [normalize_path(p) for p in config.get('exclude', [])]
    include_exts = config.get('include_extensions', [])

    # Exclude always wins (most specific rule wins)
    if match_any(path, exclude):
        return False
    if match_any(path, include):
        return True
    for ext in include_exts:
        if path.endswith(ext):
            return True
    return False

def build_tree_structure(paths):
    tree = {}
    for file_path in paths:
        parts = file_path.split('/')
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current.setdefault(part, None)
            else:
                current = current.setdefault(part, {})
    def build(node):
        nodes = []
        for name, child in sorted(node.items()):
            if child is None:
                nodes.append({'type': 'file', 'name': name})
            else:
                nodes.append({'type': 'dir', 'name': name, 'children': build(child)})
        return nodes
    return build(tree)

def format_tree(tree, indent=0):
    result = ""
    for node in tree:
        prefix = '    ' * indent
        if node['type'] == 'dir':
            result += f"{prefix}[{node['name']}/]\n"
            result += format_tree(node['children'], indent + 1)
        else:
            result += f"{prefix}{node['name']}\n"
    return result

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

def retrieve_info(config, token):
    url = config['github_url']
    owner, repo, branch = parse_github_url(url)
    output = ""

    # Fetch full repo tree once
    tree = fetch_tree(owner, repo, branch, token)
    all_paths = [item['path'] for item in tree if item['type'] == 'blob']
    included_files = [path for path in all_paths if should_include_file(path, config)]

    # Check if repo is public for raw fetch optimization
    is_public = is_public_repo(owner, repo) if not token else False

    # Special handling for README.md
    try:
        if should_include_file('README.md', config):
            if is_public:
                readme_content = fetch_raw_content(owner, repo, branch, 'README.md')
            else:
                file_info = fetch_content(owner, repo, 'README.md', branch, token)
                readme_content = decode_file_content(file_info)
            output += f"README.md:\n```\n{readme_content}\n```\n\n"
    except Exception as e:
        output += f"README.md:\n```\n# ERROR: Could not fetch README.md: {e}\n```\n\n"

    directory_tree = build_tree_structure(included_files)
    output += "Directory Structure:\n" + format_tree(directory_tree) + "\n"

    # Fetch all included files in parallel (except README.md, which is handled above)
    contents = fetch_all_contents(owner, repo, included_files, branch, token, is_public)

    for path in included_files:
        if path == 'README.md':
            continue
        content = contents.get(path, '')
        if path.endswith('.ipynb'):
            try:
                content = ipynb_to_py(content)
            except Exception as e:
                content = f"# Failed to convert {path}: {e}"
        if content.strip():
            output += f"\n{path}:\n```\n{content}\n```\n"
    return output, repo, branch

def get_output_filename(repo, branch):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_repo = re.sub(r'[^a-zA-Z0-9_-]', '_', repo)
    safe_branch = re.sub(r'[^a-zA-Z0-9_-]', '_', branch)
    return f"output_{safe_repo}_{safe_branch}_{now}.txt"

if __name__ == "__main__":
    load_dotenv()

    # Get config path from CLI argument, else default to config.yaml
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} not found! Please provide a valid config YAML.")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'include' not in config: config['include'] = []
    if 'exclude' not in config: config['exclude'] = []
    if 'include_extensions' not in config: config['include_extensions'] = []

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass("Enter your GitHub personal access token (hidden): ")

    result, repo, branch = retrieve_info(config, token)

    # Compose output file name based on repo, branch, datetime
    output_filename = get_output_filename(repo, branch)
    with open(output_filename, 'w', encoding='utf-8') as out_f:
        out_f.write(result)
    print(f"Result saved to {output_filename}")
