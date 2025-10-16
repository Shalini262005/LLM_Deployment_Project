# 🧠 Flask LLM Deployment API

This project hosts a Flask-based API endpoint designed to automatically generate, modify, and deploy GitHub repositories based on JSON tasks received from evaluators.  
It integrates **Google Gemini**, **GitHub API**, and **Flask** to dynamically build and update projects as part of an evaluation workflow.

---

## 🚀 Features

- Accepts POST requests with JSON payloads via `/api-endpoint`
- Validates incoming requests using a shared secret key
- Uses **Gemini (Google Generative AI)** to generate web app files (`index.html`, `README.md`, `LICENSE`)
- Automatically:
  - Initializes a new GitHub repository
  - Commits and pushes generated files
  - Enables **GitHub Pages**
  - Returns `repo_url`, `commit_sha`, and `pages_url` to the evaluator
- Handles **Round 2** updates — modifies repo and pushes updates

---

## 🧩 Tech Stack

- **Backend:** Python (Flask)  
- **AI Model:** Google Gemini API  
- **Version Control:** Git + GitHub API (via PyGithub)  
- **Deployment:** Render / GitHub Pages  

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Shalini262005/flask-deploy-api.git
cd flask-deploy-api
````

### 2️⃣ Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file in the project root with:

```bash
GITHUB_TOKEN=ghp_your_personal_access_token
GEMINI_API_KEY=your_gemini_api_key
API_SECRET=abcd1234
GITHUB_USER=Your github username
PORT=8000
```

---

## ▶️ Run Locally

```bash
python app.py
```

Your Flask API will start at:
`http://127.0.0.1:8000/api-endpoint`

---

## 🧪 Example Request

```bash
curl http://127.0.0.1:8000/api-endpoint \
  -H "Content-Type: application/json" \
  -d '{
        "email": "xxxxxxxxxxxxxxxxxxxxxxx.in",
        "task": "markdown-to-html-demo",
        "round": 1,
        "nonce": "abcd1234",
        "brief": "Create a simple webpage that displays Hello from Gemini and a timestamp.",
        "secret": "abcd1234",
        "evaluation_url": "http://example.com/evaluate"
      }'
```

---

## 🧱 Project Structure

```
├── app.py               # Main Flask application
├── evaluate.py
├── requirements.txt     # Dependencies
├── Procfile             # Render deployment file
├── README.md            # Documentation
└── .env.example         # Example environment variables
```


```
