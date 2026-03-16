import os
import shutil
import subprocess
import requests
import datetime
import urllib.parse
from dotenv import load_dotenv
from flask import Flask, render_template, request, Response

app = Flask(__name__)

def mask_credentials(url):
    import re
    return re.sub(r'://[^@]+@', '://***:***@', url)

def run_git_command(command, cwd=None):
    """Generator to run a command and yield output in SSE format."""
    safe_cmd = " ".join([mask_credentials(c) if "://" in c else c for c in command])
    yield f"data: > {safe_cmd}\n\n"
    
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in iter(process.stdout.readline, ''):
        yield f"data: {line}\n\n"
        
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        yield f"data: ERROR: Git command returned non-zero exit code {return_code}\n\n"
        raise subprocess.CalledProcessError(return_code, command)

def get_github_repo(api_url, owner, repo, token):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"{api_url}/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def create_gitlab_repo(api_url, namespace, repo_name, token, description, is_private):
    headers = {"Private-Token": token, "Content-Type": "application/json"}
    payload = {
        "name": repo_name,
        "description": description or f"Mirrored repository {repo_name}",
        "visibility": "private" if is_private else "public"
    }
    
    namespace_id = None
    if namespace:
        ns_response = requests.get(f"{api_url}/namespaces?search={namespace}", headers=headers)
        if ns_response.status_code == 200:
            for ns in ns_response.json():
                if ns.get('path') == namespace or ns.get('full_path') == namespace:
                    namespace_id = ns['id']
                    break
    if namespace_id:
        payload["namespace_id"] = namespace_id

    response = requests.post(f"{api_url}/projects", headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()
    elif response.status_code == 400 and 'has already been taken' in response.text:
        project_path = f"{namespace}/{repo_name}" if namespace else repo_name
        encoded_path = requests.utils.quote(project_path, safe='')
        get_response = requests.get(f"{api_url}/projects/{encoded_path}", headers=headers)
        get_response.raise_for_status()
        return get_response.json()
    else:
        response.raise_for_status()

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/migrate-auto', methods=['POST'])
def migrate_auto():
    repo_name = request.form.get('repo_name')
    
    def generate():
        try:
            if not repo_name:
                yield "data: ERROR: Target Repository Name is required.\n\n"
                return
                
            load_dotenv()
            gh_token = os.getenv("GITHUB_TOKEN")
            gh_owner = os.getenv("GITHUB_OWNER")
            gh_repo = repo_name
            gl_token = os.getenv("GITLAB_TOKEN")
            gl_namespace = os.getenv("GITLAB_NAMESPACE", "")
            
            gh_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
            gl_api_url = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4").rstrip("/")
            
            if not all([gh_token, gh_owner, gh_repo, gl_token]):
                yield "data: ERROR: Missing essential configuration (GITHUB_TOKEN, GITHUB_OWNER, Target Repo, GITLAB_TOKEN)\n\n"
                return

            yield f"data: [INFO] Fetching GitHub repository: {gh_owner}/{gh_repo}\n\n"
            gh_repo_data = get_github_repo(gh_api_url, gh_owner, gh_repo, gh_token)
            
            yield "data: [INFO] Preparing GitLab destination repository...\n\n"
            gl_repo_data = create_gitlab_repo(
                gl_api_url, gl_namespace, gh_repo, gl_token, 
                gh_repo_data.get("description", ""), 
                gh_repo_data.get("private", True)
            )
            
            gh_clone_url = gh_repo_data.get("clone_url")
            gl_clone_url = gl_repo_data.get("http_url_to_repo")
            
            gh_auth_url = gh_clone_url.replace("https://", f"https://x-access-token:{gh_token}@")
            gl_auth_url = gl_clone_url.replace("https://", f"https://oauth2:{gl_token}@")
            
            temp_dir = f"{gh_repo}.git"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            yield "data: [INFO] Cloning bare repository...\n\n"
            yield from run_git_command(["git", "clone", "--bare", gh_auth_url, temp_dir])
            
            yield "data: [INFO] Mirror pushing to GitLab...\n\n"
            yield from run_git_command(["git", "push", "--mirror", gl_auth_url], cwd=temp_dir)
            
            yield "data: [INFO] Creating local backup archive...\n\n"
            backup_dir = os.getenv("BACKUP_DIR", "./backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{gh_repo}_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_filename)
            archive_path = shutil.make_archive(backup_path, 'gztar', root_dir='.', base_dir=temp_dir)
            
            yield f"data: [INFO] Backup created at: {archive_path}\n\n"
            
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            yield "data: [SUCCESS] Automated Migration Completed!\n\n"
        except Exception as e:
            yield f"data: [ERROR] Migration failed: {str(e)}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/migrate-manual', methods=['POST'])
def migrate_manual():
    source_url = request.form.get('source_url')
    dest_url = request.form.get('dest_url')
    
    def generate():
        try:
            if not source_url or not dest_url:
                yield "data: ERROR: Source and Destination URLs are required.\n\n"
                return
                
            parsed_src = urllib.parse.urlparse(source_url)
            repo_name = parsed_src.path.split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
                
            temp_dir = f"{repo_name}_manual.git"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            yield f"data: [INFO] Started Manual Migration - Cloning {repo_name}\n\n"
            yield from run_git_command(["git", "clone", "--bare", source_url, temp_dir])
            
            yield "data: [INFO] Mirror pushing to destination...\n\n"
            yield from run_git_command(["git", "push", "--mirror", dest_url], cwd=temp_dir)
            
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            yield "data: [SUCCESS] Platform-Agnostic Migration Completed!\n\n"
        except Exception as e:
            yield f"data: [ERROR] Migration failed: {str(e)}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
