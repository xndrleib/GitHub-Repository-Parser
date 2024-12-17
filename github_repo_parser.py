import requests
import base64
from urllib.parse import urlparse
import nbformat
from nbconvert import PythonExporter
import os
import getpass
import re

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
    # Convert .ipynb to .py code
    notebook = nbformat.reads(nb_string, as_version=4)
    code, _ = PythonExporter().from_notebook_node(notebook)
    # Clean the code to reduce token usage
    code = clean_converted_code(code)
    return code

def clean_converted_code(code: str) -> str:
    lines = code.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove IPython magic commands
        if stripped.startswith('get_ipython()'):
            continue
        # Remove environment shebang and coding lines
        if stripped.startswith('#!') or stripped.startswith('# coding:'):
            continue
        # Remove markdown headers (e.g. '# # Something')
        if stripped.startswith('# #'):
            continue
        # Remove cell markers like '# In[23]', '# In[ ]:', etc.
        if re.match(r'# In\[.*\]:?', stripped):
            continue
        # Remove multiple consecutive blank lines
        if stripped == '':
            if cleaned_lines and cleaned_lines[-1].strip() == '':
                continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip() + '\n'

def build_tree(owner, repo, path, branch, token, exclude, allowed):
    items = fetch_content(owner, repo, path, branch, token)
    tree = []
    collected_paths = []
    default_extensions = ['.py', '.ipynb', '.html', '.css', '.js', '.jsx', '.rst', '.md']

    for item in items:
        # Skip .github directories, excluded patterns, and README.md since it's handled separately
        if ('.github' in item['path'].split('/') or 
            (exclude and any(x for x in exclude if x and x in item['path'])) or 
            item['name'] == 'README.md'):
            continue

        if item['type'] == 'dir':
            subtree, subpaths = build_tree(owner, repo, item['path'], branch, token, exclude, allowed)
            tree.append({'type': 'dir', 'name': item['name'], 'children': subtree})
            collected_paths.extend(subpaths)
        else:
            tree.append({'type': 'file', 'name': item['name']})
            exts = allowed if allowed else default_extensions
            if any(item['name'].endswith(ext.strip()) for ext in exts):
                collected_paths.append(item['path'])

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

def retrieve_info(url, token, exclude, allowed):
    owner, repo, branch = parse_github_url(url)
    output = ""

    # Fetch and print README once
    try:
        readme_info = fetch_content(owner, repo, 'README.md', branch, token)
        readme_content = decode_file_content(readme_info)
        output += f"README.md:\n```\n{readme_content}\n```\n\n"
    except:
        output += "README.md: Not found or error fetching README\n\n"

    directory_tree, file_paths = build_tree(owner, repo, '', branch, token, exclude, allowed)
    output += "Directory Structure:\n" + format_tree(directory_tree) + "\n"

    # Fetch and process files (excluding README.md)
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
    github_url = input("Enter the GitHub repository URL: ")
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass("Enter your GitHub personal access token (hidden): ")

    exclude_str = input("Enter comma-separated file or directory names to exclude (optional): ")
    exclude = [x.strip() for x in exclude_str.split(',')] if exclude_str else None

    exts_str = input("Enter comma-separated file extensions to parse (optional, e.g., .py,.ipynb,.md): ")
    allowed_exts = [x.strip() for x in exts_str.split(',')] if exts_str else None

    result = retrieve_info(github_url, token, exclude, allowed_exts)
    print(result)
