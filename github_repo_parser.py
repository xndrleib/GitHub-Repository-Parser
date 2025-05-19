# -*- coding: utf-8 -*-
"""GitHub Repo Parser"""

import requests
import base64
from urllib.parse import urlparse
import nbformat
from nbconvert import PythonExporter
import os
import getpass
import re
import fnmatch
import yaml
from dotenv import load_dotenv

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

def fetch_content(owner, repo, path='', branch='main', token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
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

def match_any(path, patterns):
    if not patterns:
        return False
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)

def should_include_file(path, config):
    include = config.get('include', [])
    exclude = config.get('exclude', [])
    include_exts = config.get('include_extensions', [])

    if match_any(path, include):
        return True
    for ext in include_exts:
        if path.endswith(ext):
            return True
    if match_any(path, exclude):
        return False
    return False

def build_tree(owner, repo, path, branch, token, config):
    items = fetch_content(owner, repo, path, branch, token)
    tree = []
    collected_paths = []
    for item in items:
        item_path = item['path']
        if '.github' in item_path.split('/'):
            continue
        if item['type'] == 'dir':
            subtree, subpaths = build_tree(owner, repo, item_path, branch, token, config)
            if subtree:
                tree.append({'type': 'dir', 'name': item['name'], 'children': subtree})
                collected_paths.extend(subpaths)
        else:
            if should_include_file(item_path, config):
                tree.append({'type': 'file', 'name': item['name']})
                collected_paths.append(item_path)
    return tree, collected_paths

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

def retrieve_info(config, token):
    url = config['github_url']
    owner, repo, branch = parse_github_url(url)
    output = ""
    try:
        readme_info = fetch_content(owner, repo, 'README.md', branch, token)
        readme_content = decode_file_content(readme_info)
        if should_include_file('README.md', config):
            output += f"README.md:\n```\n{readme_content}\n```\n\n"
    except Exception as e:
        pass
    directory_tree, file_paths = build_tree(owner, repo, '', branch, token, config)
    output += "Directory Structure:\n" + format_tree(directory_tree) + "\n"
    for path in file_paths:
        file_info = fetch_content(owner, repo, path, branch, token)
        content = decode_file_content(file_info)
        if path.endswith('.ipynb'):
            try:
                content = ipynb_to_py(content)
            except Exception as e:
                content = f"# Failed to convert {path}: {e}"
        if content.strip():
            output += f"\n{path}:\n```\n{content}\n```\n"
    return output

if __name__ == "__main__":
    load_dotenv()  # Load .env for GITHUB_TOKEN

    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        raise FileNotFoundError("config.yaml not found! Please create one.")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'include' not in config: config['include'] = []
    if 'exclude' not in config: config['exclude'] = []
    if 'include_extensions' not in config: config['include_extensions'] = []

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass("Enter your GitHub personal access token (hidden): ")

    result = retrieve_info(config, token)

    # Save result to output.txt
    with open('output.txt', 'w', encoding='utf-8') as out_f:
        out_f.write(result)
    print("Result saved to output.txt")
