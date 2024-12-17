import requests
import base64
from urllib.parse import urlparse
import nbformat
from nbconvert import PythonExporter
import os
import getpass

def parse_github_url(url):
    """
    Parses the GitHub URL and extracts the repository owner, name, and branch if specified.
    """
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip("/").split("/")
    if len(path_segments) >= 2:
        owner, repo = path_segments[0], path_segments[1]
        branch = 'main'
        if 'tree' in path_segments:
            tree_index = path_segments.index('tree')
            if tree_index + 1 < len(path_segments):
                branch = path_segments[tree_index + 1]
        return owner, repo, branch
    else:
        raise ValueError("Invalid GitHub URL provided!")

def fetch_repo_content(owner, repo, path='', branch='main', token=None):
    """
    Fetches the content of the GitHub repository at the specified branch.
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {'ref': branch}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_file_content(file_info):
    """
    Retrieves and decodes the content of files.
    """
    if file_info.get('encoding') == 'base64':
        return base64.b64decode(file_info['content']).decode('utf-8')
    else:
        return file_info.get('content', '')

def build_directory_tree(owner, repo, path='', branch='main', token=None, exclude_files=None, allowed_extensions=None):
    """
    Builds the directory tree and collects file paths, while excluding specified files and filtering by allowed extensions.
    """
    items = fetch_repo_content(owner, repo, path, branch, token)
    tree = []
    file_paths = []
    for item in items:
        if '.github' in item['path'].split('/'):
            continue
        item_name = item['name']
        item_path = item['path']
        # Exclude files or directories if specified
        if exclude_files and any(ex_file.strip() and ex_file in item_path for ex_file in exclude_files):
            continue
        if item['type'] == 'dir':
            subtree, subpaths = build_directory_tree(owner, repo, item_path, branch, token, exclude_files, allowed_extensions)
            tree.append({'type': 'dir', 'name': item_name, 'children': subtree})
            file_paths.extend(subpaths)
        else:
            tree.append({'type': 'file', 'name': item_name})
            # Include file only if it matches allowed extensions
            if allowed_extensions:
                if any(item_name.endswith(ext.strip()) for ext in allowed_extensions):
                    file_paths.append(item_path)
            else:
                # If for some reason allowed_extensions is None, fallback to default
                default_extensions = ['.py', '.ipynb', '.html', '.css', '.js', '.jsx', '.rst', '.md']
                if any(item_name.endswith(ext) for ext in default_extensions):
                    file_paths.append(item_path)
    return tree, file_paths

def join_directory_tree(tree, indent=0):
    """
    Creates a formatted string of the directory structure from the tree data.
    """
    tree_str = ""
    for node in tree:
        if node['type'] == 'dir':
            tree_str += '    ' * indent + f"[{node['name']}/]\n"
            tree_str += join_directory_tree(node['children'], indent + 1)
        else:
            tree_str += '    ' * indent + f"{node['name']}\n"
    return tree_str

def retrieve_github_repo_info(url, token=None, exclude_files=None, allowed_extensions=None):
    """
    Retrieves and formats repository information, including README, the directory tree,
    and file contents, while handling branch selection and excluding specified files,
    as well as filtering by allowed extensions.
    """
    owner, repo, branch = parse_github_url(url)

    formatted_string = ""

    try:
        readme_info = fetch_repo_content(owner, repo, 'README.md', branch, token)
        readme_content = get_file_content(readme_info)
        formatted_string += f"README.md:\n```\n{readme_content}\n```\n\n"
    except Exception as e:
        formatted_string += "README.md: Not found or error fetching README\n\n"

    directory_tree, file_paths = build_directory_tree(owner, repo, branch=branch, token=token, exclude_files=exclude_files, allowed_extensions=allowed_extensions)
    directory_structure = join_directory_tree(directory_tree)
    formatted_string += f"Directory Structure:\n{directory_structure}\n"

    contents = {}
    for path in file_paths:
        file_info = fetch_repo_content(owner, repo, path, branch, token)
        file_content = get_file_content(file_info)
        file_name = path.split('/')[-1]
        if file_name.endswith('.ipynb'):
            try:
                file_content = ipynb_to_py(file_content)
            except Exception as e:
                print(f'Failed to process {file_name}:\n{e}')
        contents[path] = file_content

    for path, file_content in contents.items():
        if file_content.strip():
            formatted_string += f"\n{path}:\n"
            formatted_string += '```\n'
            formatted_string += file_content + '\n'
            formatted_string += '```\n'

    return formatted_string

def ipynb_to_py(ipynb_string):
    """
    Converts a Jupyter notebook JSON string to Python (.py) code.
    """
    notebook = nbformat.reads(ipynb_string, as_version=4)
    python_exporter = PythonExporter()
    python_code, _ = python_exporter.from_notebook_node(notebook)
    return python_code

if __name__ == "__main__":
    github_url = input("Enter the GitHub repository URL: ")
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass("Enter your GitHub personal access token (hidden): ")
    exclude_files_input = input("Enter comma-separated file or directory names to exclude (optional): ")
    exclude_files = [ex.strip() for ex in exclude_files_input.split(',')] if exclude_files_input else None

    extensions_input = input("Enter comma-separated file extensions to parse (optional, e.g., .py,.ipynb,.md): ")
    allowed_extensions = [ext.strip() for ext in extensions_input.split(',')] if extensions_input else None

    formatted_output = retrieve_github_repo_info(github_url, token=token, exclude_files=exclude_files, allowed_extensions=allowed_extensions)
    print(formatted_output)
