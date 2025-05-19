# GitHub Repository Parser

This script retrieves and formats information from a GitHub repository, including:

- The repository's `README.md` content (if requested by the config)
- The directory structure
- The contents of selected files (e.g., `.py`, `.ipynb`, `.html`, etc.)

All options and filters are set in a single YAML config file.  
The script is designed for secure and repeatable use, using a `.env` file for your GitHub Personal Access Token.

---

## Features

- **YAML Configuration:**  
  All settings (repository, include/exclude lists, extensions) are managed via `config.yaml` for transparency and repeatability.

- **Explicit Filtering Logic:**  
  - **Files in the `include` list are always included,** even if excluded by their folder or extension.
  - **Files with extensions in `include_extensions` are always included,** even if excluded by their folder.
  - **Files or folders in `exclude` are always excluded,** even if their parent folder is included.
  - **"Most specific rule wins"**—see logic table below.

- **Jupyter Notebook Conversion:**  
  `.ipynb` files are automatically converted to `.py` code.

- **Branch Selection:**  
  Supports specifying a branch by including it in the repo URL.

- **Automatic Output Saving:**  
  Results are always written to `output.txt` for convenience.

- **Secure Token Handling:**  
  Uses a `.env` file to keep your GitHub token secret and out of your codebase.

---

## Configuration

Create a `config.yaml` in your project directory:

```yaml
github_url: "https://github.com/youruser/yourrepo"
exclude:
  - "data/"
  - "folderA/"
  - "*.csv"
include:
  - "folderA/keepme.py"
  - "README.md"
include_extensions:
  - ".py"
  - ".ipynb"
````

* **`github_url`:** The GitHub repository URL. To specify a branch, use `/tree/branch_name` in the URL.
* **`exclude`:** List of directories, files, or glob patterns to always exclude.
* **`include`:** List of specific files to always include, even if their parent is excluded.
* **`include_extensions`:** List of file extensions (e.g., `.py`, `.ipynb`) to always include.

**All paths are relative to the repository root. Globs (e.g., `*.csv`) are supported.**

---

## How Filtering Works

| Scenario                                         | Included? | Reason                                       |
| ------------------------------------------------ | --------- | -------------------------------------------- |
| File is in `include`                             | Yes       | Always included                              |
| File matches `include_extensions`                | Yes       | Always included                              |
| File is in `exclude`                             | No        | Always excluded (most specific rule wins)    |
| Folder is in `exclude`, but file is in `include` | Yes       | File-level include takes priority            |
| Folder is in `include`, but file is in `exclude` | No        | File-level exclude takes priority            |
| File not matched by any rule                     | No        | Only included if explicitly listed or by ext |

---

## GitHub Token Security (`.env`)

Create a `.env` file in the project directory:

```
GITHUB_TOKEN=your_github_pat_here
```

Your token will be loaded automatically via [`python-dotenv`](https://github.com/theskumar/python-dotenv).
**Never commit `.env` files to version control.**

---

## Requirements

Install all dependencies with:

```bash
pip install -r requirements.txt
```
---

## Usage

1. **Edit your `config.yaml` and `.env` as shown above.**
2. **Run the script:**

   ```bash
   python github_repo_parser.py
   ```
3. **View the results in `output.txt`.**

---

### Example Workflow

**config.yaml**

```yaml
github_url: "https://github.com/example/repo"
exclude:
  - "docs/"
  - "*.csv"
include:
  - "docs/special.md"
  - "README.md"
include_extensions:
  - ".py"
```

**.env**

```
GITHUB_TOKEN=ghp_yourtoken
```

**Run:**

```bash
python github_repo_parser.py
```

---

## AI Prompt Creation Benefits

When using AI models for code review or generation, this script helps you:

* **Reduce token usage** by converting Jupyter notebooks to Python scripts.
* **Improve AI response quality** by stripping unnecessary metadata.
* **Stay within context limits** by including only relevant files.

---

## Security Notes

* **Never share or commit your GitHub token.**
* **Always use a `.env` file for credentials.**
* **Tokens are loaded securely and never echoed or logged.**
