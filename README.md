# GitHub Repository Parser

This script allows you to retrieve and format information from a GitHub repository, including:

- The repository's `README.md` content.
- The directory structure.
- The contents of specific files (e.g., `.py`, `.ipynb`, `.html`, etc.).

It supports specifying a particular branch and excluding certain files or directories from the output.

## Features

- **Branch Selection:** Parse and retrieve content from a specific branch.
- **File Exclusion:** Specify files or directories to exclude from the output.
- **File Content Retrieval:** Fetch and display contents of selected file types.
- **Jupyter Notebook Conversion:** Convert `.ipynb` files to `.py` code to save tokens and improve AI response quality.

## AI Prompt Creation

When using AI language models for code generation, assistance, or review, it's essential to provide concise and relevant prompts. This script helps in:

- **Reducing Token Usage:** By converting Jupyter notebooks (`.ipynb`) to plain Python scripts (`.py`), you reduce the number of tokens required to represent the code. Notebook JSON files are verbose and consume more tokens.
- **Improving AI Response Quality:** Simplifying the input by removing unnecessary metadata allows the AI to focus on the actual code, leading to better understanding and more accurate responses.
- **Efficient Context Management:** Keeping prompts within token limits ensures that the AI model can process the entire input without truncation, preserving important context.

## Requirements

- `requests` library
- `nbformat` library
- `nbconvert` library

You can install the required packages using:

```bash
pip install requests nbformat nbconvert
```

## Usage

### Running the Script

1. **Set Up Your GitHub Personal Access Token:**

   - Generate a personal access token from your GitHub account with the necessary permissions.
   - It's recommended to set the token as an environment variable named `GITHUB_TOKEN` to avoid exposing it in your code.

2. **Run the Script:**

   ```bash
   python github_repo_parser.py
   ```

3. **Provide the Following Inputs When Prompted:**

   - **GitHub Repository URL:** The URL of the repository you want to parse. You can include a specific branch in the URL (e.g., `https://github.com/username/repo/tree/branch_name`).
   - **GitHub Personal Access Token:** Your GitHub token if not set as an environment variable.
   - **Files or Directories to Exclude (Optional):** Comma-separated names of files or directories to exclude from the output.

### Example

```bash
Enter the GitHub repository URL: https://github.com/username/repo/tree/branch_name
Enter your GitHub personal access token: *******************
Enter comma-separated file or directory names to exclude (optional): test.ipynb, docs/
```

The script will output the formatted repository information, which you can redirect to a file if needed:

```bash
python github_repo_parser.py > output.txt
```

## Security Note

- **Do Not Share Your Token:** Keep your GitHub personal access token secure. Do not share it or commit it to version control.
- **Use Environment Variables:** Prefer setting your token as an environment variable rather than hardcoding it.
