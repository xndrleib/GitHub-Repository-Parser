# GitHub Repository Parser

This tool retrieves and formats information from a GitHub repository, including:

- The repository's `README.md` content (if requested by the config)
- The directory structure
- The contents of selected files (e.g., `.py`, `.ipynb`, `.html`, etc.)

All options and filters are set in a single YAML config file.  
Your GitHub Personal Access Token is loaded securely via a `.env` file.

---

## Features

- **Modular, Maintainable Codebase:**  
  The tool is structured as three modules:
  - `main.py` (CLI & orchestration)
  - `fetcher.py` (all GitHub/network file fetching)
  - `processor.py` (all filtering, parsing, and formatting)

- **YAML Configuration:**  
  All settings (repository, include/exclude lists, extensions) are managed via `config.yaml` (or any YAML you specify) for transparency and repeatability.

- **Explicit Filtering Logic:**  
  - **Files in the `include` list are always included,** even if excluded by their folder or extension.
  - **Files with extensions in `include_extensions` are always included,** even if excluded by their folder.
  - **Files or folders in `exclude` are always excluded,** even if their parent folder is included.
  - **"Most specific rule wins"**—see logic table below.

- **Performance Optimized:**  
  - **Parallel file content fetching** for large repositories.
  - **Uses raw.githubusercontent.com for public repos** (no API limit, even faster).
  - Detects public/private repo status automatically.

- **Jupyter Notebook Conversion:**  
  `.ipynb` files are automatically converted to `.py` code.

- **Branch Selection:**  
  Supports specifying a branch by including it in the repo URL.

- **Automatic Output Saving:**  
  The output is always written to a file named like  
  `output_{repo}_{branch}_{YYYYMMDD_HHMMSS}.txt`  
  Example: `output_Motor-Fault-Detection_denoising_20240519_210745.txt`

- **Config Path Argument:**  
  You can specify the config file as a command line argument (default: `config.yaml`).

- **Secure Token Handling:**  
  Uses a `.env` file to keep your GitHub token secret and out of your codebase.

---

## Configuration

Create a `config.yaml` in your project directory (or use a different filename):

```yaml
github_url: "https://github.com/youruser/yourrepo"
exclude:    # Do NOT leave blank! Use [] for an empty list
  - "data/"
  - "folderA/"
  - "*.csv"
include:    # Do NOT leave blank! Use [] for an empty list
  - "folderA/keepme.py"
  - "README.md"
include_extensions:
  - ".py"
  - ".ipynb"
````

* **`github_url`:** The GitHub repository URL. To specify a branch, use `/tree/branch_name` in the URL.
* **`exclude`:** List of directories, files, or glob patterns to always exclude.
  **Tip:** If not excluding anything, use `exclude: []` (YAML interprets blank as `null`).
* **`include`:** List of specific files to always include, even if their parent is excluded.
  Use `include: []` for none.
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
   python main.py
   ```

   or, to use a custom config path:

   ```bash
   python main.py my_custom_config.yaml
   ```

3. **View the results in the output file named like:**
   `output_{repo}_{branch}_{YYYYMMDD_HHMMSS}.txt`
   (The script will print the filename after running.)

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
python main.py
```

or

```bash
python main.py my_special_config.yaml
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

---

## Project Structure

```
GitHub-Repository-Parser/
├── README.md
├── config.yaml             # Your configuration file
├── .env                    # Your GitHub token (not in version control)
├── fetcher.py              # GitHub API/network logic
├── processor.py            # Filtering/conversion logic
├── main.py                 # CLI and orchestration
└── requirements.txt
```