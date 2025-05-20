# tests/test_ipynb_conversion.py

import pytest
import os
import nbformat
from processor import ipynb_to_py

TESTS_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "templates"))

def load_file(fname):
    with open(os.path.join(TESTS_DIR, fname), "r", encoding="utf-8") as f:
        return f.read()

def test_default_conversion():
    nb_data = load_file("sample_notebook.ipynb")
    py = ipynb_to_py(nb_data)
    assert "def hello_world()" in py
    # No output comments expected with default template
    assert "# ── Cell Output ──" not in py

def test_custom_template_conversion():
    nb_data = load_file("sample_notebook.ipynb")
    tpl_path = os.path.join(TEMPLATES_DIR, "python_with_output.tpl")
    opts = {
        "template_file": tpl_path,
        "extra_template_basedirs": TEMPLATES_DIR,
    }
    py = ipynb_to_py(nb_data, opts)
    assert "# ── Cell Output ──" in py
    assert "# hello" in py
