# -*- coding: utf-8 -*-
"""processor.py -- Filtering, conversion, formatting"""

import re
import fnmatch
from pathlib import PurePosixPath
import nbformat
from nbconvert import PythonExporter

def normalize_path(path):
    return str(PurePosixPath(path))

def match_any(path, patterns):
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
