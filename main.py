# -*- coding: utf-8 -*-
"""main.py -- CLI and Orchestration"""

import os
import sys
import yaml
import getpass
from dotenv import load_dotenv
from datetime import datetime
from fetcher import (
    parse_github_url, fetch_tree, fetch_content, decode_file_content,
    is_public_repo, fetch_raw_content, fetch_all_contents
)
from processor import (
    should_include_file, build_tree_structure, format_tree, ipynb_to_py
)
import re

def get_output_filename(repo, branch):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_repo = re.sub(r'[^a-zA-Z0-9_-]', '_', repo)
    safe_branch = re.sub(r'[^a-zA-Z0-9_-]', '_', branch)
    return f"output_{safe_repo}_{safe_branch}_{now}.txt"

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
    from fetcher import fetch_all_contents  # avoid circular import warning in some linters
    contents = fetch_all_contents(owner, repo, included_files, branch, token, is_public)

    for path in included_files:
        if path == 'README.md':
            continue
        content = contents.get(path, '')
        if path.endswith('.ipynb'):
            try:
                content = ipynb_to_py(content, config.get('ipynb_conversion', {}))
            except Exception as e:
                content = f"# Failed to convert {path}: {e}"
        if content.strip():
            output += f"\n{path}:\n```\n{content}\n```\n"
    return output, repo, branch

if __name__ == "__main__":
    load_dotenv()

    # Get config path from CLI argument, else default to config.yaml
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} not found! Please provide a valid config YAML.")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    for key in ['include', 'exclude', 'include_extensions']:
        if key not in config or config[key] is None:
            config[key] = []

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass("Enter your GitHub personal access token (hidden): ")

    result, repo, branch = retrieve_info(config, token)

    output_filename = get_output_filename(repo, branch)
    with open(output_filename, 'w', encoding='utf-8') as out_f:
        out_f.write(result)
    print(f"Result saved to {output_filename}")
