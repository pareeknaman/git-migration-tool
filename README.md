# Git Backup & Migration Tool

A Python script designed to seamlessly migrate or backup Git repositories from GitHub to GitLab via REST APIs. 
It clones a bare repository securely, preserves history (tags and branches), pushes as a mirror to GitLab, and creates a local compressed `.tar.gz` cold backup of the repository.

## Requirements
- Python 3.7+
- Git installed on host machine

## Setup
1. Clone or download this project.
2. Install python dependencies:
```bash
pip install -r requirements.txt
```
3. Setup environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your Personal Access Tokens for GitHub and GitLab
   - Provide the exact GitHub Repo Owner and Name (`GITHUB_OWNER`, `GITHUB_REPO`)
   - (Optional) Customize `BACKUP_DIR` for your local cold backups

## Usage
Simply run the python script:
```bash
python3 migrate.py
```

## Security
This script dynamically embeds your tokens for `git` operations directly into network calls without storing them in Git config or logging them. All subprocess output handles token masking if network errors occur.

## Errors & Debugging
If a migration fails, the script will gracefully hide your tokens from any standard output error stacks. Always verify personal access token permissions if you face 401 Unauthorized errors. Minimum token requirements:
- GitHub: `repo` scope.
- GitLab: `api`, `read_repository`, `write_repository` scopes.
