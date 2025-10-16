# evaluate.py
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/evaluate_callback", methods=["POST"])
def evaluate_callback():
    payload = request.get_json(force=True)
    print("\n=== Received callback ===")
    print(payload)

    repo_url = payload.get("repo_url")
    pages_url = payload.get("pages_url")

    results = []
    if repo_url:
        # check LICENSE
        license_raw = repo_url.replace("github.com", "raw.githubusercontent.com") + "/main/LICENSE"
        r = requests.get(license_raw)
        if r.ok and "MIT" in r.text:
            results.append({"check": "MIT LICENSE", "status": "PASS"})
        else:
            results.append({"check": "MIT LICENSE", "status": "FAIL"})

    if pages_url:
        r = requests.get(pages_url)
        results.append({"check": "Pages reachable (200)", "status": "PASS" if r.status_code == 200 else "FAIL"})

    print("== Results:", results)
    return jsonify({"results": results}), 200

if __name__ == "__main__":
    app.run(port=5000)
