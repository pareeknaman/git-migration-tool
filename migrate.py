#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import requests
import re
import datetime
from dotenv import load_dotenv

def mask_credentials(text):
    if not text:
        return text
    # Mask anything between https:// and @ to hide tokens in URLs
    return re.sub(r'https://[^@]+@', 'https://***:***@', text)

def check_env_vars(*args):
    missing = [arg for arg in args if not os.environ.get(arg)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Please ensure your .env file is correctly configured.")
        sys.exit(1)

def run_command(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        masked_cmd = " ".join([mask_credentials(c) for c in command])
        print(f"Error executing command: {masked_cmd}")
        print(f"Stdout: {mask_credentials(e.stdout)}")
        print(f"Stderr: {mask_credentials(e.stderr)}")
        print("Migration failed during git operations.")
        sys.exit(1)

def get_github_repo(api_url, owner, repo, token):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"{api_url}/repos/{owner}/{repo}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch GitHub repository '{owner}/{repo}'.")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            if e.response.status_code == 404:
                print("Repository not found or token lacks access.")
            elif e.response.status_code == 401:
                print("Unauthorized. Please check your GITHUB_TOKEN.")
        sys.exit(1)

def create_gitlab_repo(api_url, namespace, repo_name, token, description, is_private):
    headers = {
        "Private-Token": token,
        "Content-Type": "application/json"
    }
    
    # 1. Resolve namespace ID if namespace is provided
    namespace_id = None
    if namespace:
        try:
            ns_response = requests.get(f"{api_url}/namespaces?search={namespace}", headers=headers)
            ns_response.raise_for_status()
            namespaces = ns_response.json()
            for ns in namespaces:
                if ns.get('path') == namespace or ns.get('full_path') == namespace:
                    namespace_id = ns['id']
                    break
            if not namespace_id:
                print(f"Warning: Could not find exact match for namespace '{namespace}'. Will create under personal user space.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to search for Gitlab namespace '{namespace}'. Proceeding without namespace...")
            
    # 2. Try to create the project
    payload = {
        "name": repo_name,
        "description": description or f"Mirrored repository {repo_name}",
        "visibility": "private" if is_private else "public"
    }
    if namespace_id:
        payload["namespace_id"] = namespace_id
        
    try:
        response = requests.post(f"{api_url}/projects", headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"Successfully created GitLab repository: {repo_name}")
            return response.json()
        elif response.status_code == 400 and 'has already been taken' in response.text:
            print(f"GitLab repository '{repo_name}' already exists. We will push and mirror to the existing one.")
            
            # Retrieve existing project information
            project_path = f"{namespace}/{repo_name}" if namespace else repo_name
            encoded_path = requests.utils.quote(project_path, safe='')
            
            get_response = requests.get(f"{api_url}/projects/{encoded_path}", headers=headers)
            get_response.raise_for_status()
            return get_response.json()
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Failed to ensure destination Gitlab repository.")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            if e.response.status_code == 401:
                print("Unauthorized. Please check your GITLAB_TOKEN.")
             
        sys.exit(1)

def main():
    print("===================================================")
    print("        Git Backup & Migration Tool (GH -> GL)      ")
    print("===================================================\n")
    
    # Load from .env file
    load_dotenv()
    
    check_env_vars("GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO", "GITLAB_TOKEN")
    
    gh_token = os.getenv("GITHUB_TOKEN")
    gh_owner = os.getenv("GITHUB_OWNER")
    gh_repo = os.getenv("GITHUB_REPO")
    
    gl_token = os.getenv("GITLAB_TOKEN")
    gl_namespace = os.getenv("GITLAB_NAMESPACE", "")
    
    gh_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    gl_api_url = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4").rstrip("/")
    backup_dir = os.getenv("BACKUP_DIR", "./backups")
    
    # [Step 1]
    print(f"[1/6] Fetching repository information from GitHub: {gh_owner}/{gh_repo}...")
    gh_repo_data = get_github_repo(gh_api_url, gh_owner, gh_repo, gh_token)
    repo_description = gh_repo_data.get("description", "")
    is_private = gh_repo_data.get("private", True)
    
    # [Step 2]
    print("\n[2/6] Preparing destination repository on GitLab...")
    gl_repo_data = create_gitlab_repo(gl_api_url, gl_namespace, gh_repo, gl_token, repo_description, is_private)
    
    # URLs Extraction
    gh_clone_url = gh_repo_data.get("clone_url")
    if not gh_clone_url:
        print("Error: Could not retrieve clone_url from GitHub response.")
        sys.exit(1)
    # Inject auth into GitHub URL   
    gh_auth_url = gh_clone_url.replace("https://", f"https://x-access-token:{gh_token}@")
    
    gl_clone_url = gl_repo_data.get("http_url_to_repo")
    if not gl_clone_url:
        print("Error: Could not retrieve http_url_to_repo from GitLab response.")
        sys.exit(1)
    # Inject auth into GitLab URL
    gl_auth_url = gl_clone_url.replace("https://", f"https://oauth2:{gl_token}@")
    
    temp_dir = f"{gh_repo}.git"
    
    try:
        # [Step 3] Clone bare from Github
        print(f"\n[3/6] Cloning bare repository from GitHub into temporary directory...")
        if os.path.exists(temp_dir):
            print(f"Warning: Temporary directory '{temp_dir}' already exists. Removing it...")
            shutil.rmtree(temp_dir)
            
        run_command(["git", "clone", "--bare", gh_auth_url])
        print("Successfully cloned bare repository.")
        
        # [Step 4] Push mirror to Gitlab
        print("\n[4/6] Pushing mirror to GitLab...")
        run_command(["git", "push", "--mirror", gl_auth_url], cwd=temp_dir)
        print("Successfully pushed mirror repository.")
        
        # [Step 5] Create local cold backup
        print("\n[5/6] Creating local cold backup...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{gh_repo}_{timestamp}"
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_path = os.path.join(backup_dir, backup_filename)
        archive_path = shutil.make_archive(backup_path, 'gztar', root_dir='.', base_dir=temp_dir)
        print(f"Successfully created local backup at: {archive_path}")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred during Git operations: {e}")
        sys.exit(1)
        
    finally:
        # [Step 6] Cleanup
        print("\n[6/6] Cleaning up...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Removed temporary directory '{temp_dir}'.")
            
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    main()
