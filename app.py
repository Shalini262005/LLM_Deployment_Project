import os
import json
import subprocess
import tempfile
import time
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from github import Github
import google.generativeai as genai

# ------------------ Setup ------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_SECRET = os.getenv("API_SECRET")
GITHUB_USER = os.getenv("GITHUB_USER")
PORT = int(os.getenv("PORT", 8000))

gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
app = Flask(__name__)

# ------------------ Helpers ------------------
def run(cmd, cwd=None):
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def notify_evaluator(evaluation_url, body, max_attempts=6):
    delay = 1
    for attempt in range(max_attempts):
        try:
            r = requests.post(evaluation_url, json=body, timeout=20)
            if r.status_code == 200:
                return True
            print("Evaluator returned", r.status_code, r.text)
        except Exception as e:
            print("Notify error:", e)
        time.sleep(delay)
        delay *= 2
    return False

def generate_files_with_gemini(brief: str):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""
You are an expert web developer.
Generate a minimal static website based on this task brief:

{brief}

Return JSON with keys: index.html, README.md, LICENSE
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        files = json.loads(text)
        return files
    except Exception as e:
        print("Gemini error, fallback:", e)
        return {
            "index.html": f"<html><body><h1>{brief}</h1><p>Hello from Gemini fallback.</p></body></html>",
            "README.md": f"# {brief}\n\nGenerated automatically using Gemini.",
            "LICENSE": "MIT License\n\nCopyright (c)..."
        }

def enable_github_pages(user, repo_name):
    """Enable GitHub Pages using REST API"""
    enable_url = f"https://api.github.com/repos/{user}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    payload_pages = {"source": {"branch": "main", "path": "/"}}
    try:
        print("Enabling GitHub Pages...")
        r = requests.post(enable_url, headers=headers, json=payload_pages)
        print("GitHub Pages response:", r.status_code, r.text)
    except Exception as e:
        print("GitHub Pages enable error:", e)

    pages_url = f"https://{user}.github.io/{repo_name}/"
    # Wait for deployment
    for attempt in range(12):
        try:
            resp = requests.get(pages_url, timeout=10)
            if resp.status_code == 200:
                print("✅ GitHub Pages is live:", pages_url)
                return pages_url
        except Exception:
            pass
        print(f"Waiting for GitHub Pages... ({attempt+1}/12)")
        time.sleep(5)
    print("⚠️ Pages may still be deploying.")
    return pages_url

# ------------------ API Endpoint ------------------
@app.route("/api-endpoint", methods=["POST"])
def api_endpoint():
    payload = request.get_json(force=True)
    if payload.get("secret") != API_SECRET:
        return jsonify({"error": "invalid secret"}), 403

    email = payload.get("email")
    task = payload.get("task")
    round_idx = payload.get("round", 1)
    nonce = payload.get("nonce", "xx")
    brief = payload.get("brief", "")
    evaluation_url = payload.get("evaluation_url")

    import datetime, random, string
    safe_task = task.replace(" ", "-").replace("/", "-")[:30]
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    repo_name = f"{safe_task}-{timestamp}-{rand_suffix}"

    workdir = Path(tempfile.mkdtemp(prefix="student_build_"))
    print("Workdir:", workdir)

    # ------------------ Round 1 ------------------
    if round_idx == 1:
        repo_dir = workdir / repo_name
        repo_dir.mkdir()
        files = generate_files_with_gemini(brief)
        for name, content in files.items():
            (repo_dir / name).write_text(content, encoding="utf-8")

        run(["git", "init"], cwd=str(repo_dir))
        run(["git", "config", "user.email", "shalinisivakumar06@gmail.com"], cwd=str(repo_dir))
        run(["git", "config", "user.name", "Shalini262005"], cwd=str(repo_dir))
        run(["git", "add", "."], cwd=str(repo_dir))
        run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_dir))


        if gh:
            user = gh.get_user()
            print("Creating repo on GitHub:", repo_name)
            repo = user.create_repo(repo_name, private=False, description=f"Auto-created for task {task}")
            origin = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{user.login}/{repo_name}.git"
            run(["git", "remote", "add", "origin", origin], cwd=str(repo_dir))
            run(["git", "branch", "-M", "main"], cwd=str(repo_dir))
            run(["git", "push", "-u", "origin", "main"], cwd=str(repo_dir))
            repo_url = f"https://github.com/{user.login}/{repo_name}"
            pages_url = enable_github_pages(user.login, repo_name)
        else:
            return jsonify({"error": "Missing GitHub credentials"}), 500

        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_dir)).decode().strip()
        payload_out = {
            "email": email,
            "task": task,
            "round": round_idx,
            "nonce": nonce,
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        ok = notify_evaluator(evaluation_url, payload_out)
        if not ok:
            return jsonify({"error": "failed to notify evaluator"}), 500
        return jsonify(payload_out), 200

    # ------------------ Round 2 ------------------
    else:
        repo_url_git = payload.get("repo_url")
        if not repo_url_git:
            return jsonify({"error": "repo_url not provided for round > 1"}), 400

        repo_dir = workdir / "repo_clone"
        try:
            run(["git", "clone", repo_url_git, str(repo_dir)])
        except Exception as e:
            return jsonify({"error": f"failed to clone repo: {e}"}), 500

        # Modify project using Gemini
        files = generate_files_with_gemini(brief)
        for name, content in files.items():
            (repo_dir / name).write_text(content, encoding="utf-8")

        # Ensure Git user identity is configured before committing
        run(["git", "config", "user.email", "shalinisivakumar06@gmail.com"], cwd=str(repo_dir))
        run(["git", "config", "user.name", "Shalini262005"], cwd=str(repo_dir))

        run(["git", "add", "."], cwd=str(repo_dir))
        run(["git", "commit", "-m", "Round 2 update"], cwd=str(repo_dir))

        if gh and GITHUB_TOKEN:
            token_remote = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_url_git.split('/')[-1]}"
            run(["git", "remote", "set-url", "origin", token_remote], cwd=str(repo_dir))
            run(["git", "branch", "-M", "main"], cwd=str(repo_dir))  # Ensure main branch
            run(["git", "push", "-u", "origin", "main"], cwd=str(repo_dir))
        else:
            return jsonify({"error": "Missing GitHub credentials"}), 500

        commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_dir)).decode().strip()
        pages_url = enable_github_pages(GITHUB_USER, repo_url_git.split("/")[-1])
        payload_out = {
            "email": email,
            "task": task,
            "round": round_idx,
            "nonce": nonce,
            "repo_url": repo_url_git,
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        ok = notify_evaluator(evaluation_url, payload_out)
        if not ok:
            return jsonify({"error": "failed to notify evaluator"}), 500
        return jsonify(payload_out), 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "LLM Deployment API is live!",
        "endpoints": ["/api-endpoint (POST)"]
    })


# ------------------ Run App ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
