# Civic User Management Service

This microservice handles **user registration, authentication, and leaderboard management** for the Civic Issues platform.  
It is built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, designed for scalability and cloud deployment (including Kubernetes).

---

### Step 1: Set Up Python Enviornment
Create a virtual environment:
```python
python3 -m venv venv
```

Activate the virtual environment.

On macOS/Linux:
```bash
source venv/bin/activate
```
On Windows (Git Bash):
```bash
source venv/Scripts/activate
```

Install all required libraries (this assumes you have a requirements.txt file in your repo):
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Your app needs to know how to connect to your new database. We do this with a `.env` file, which must not be committed to Git.

1. Create a new file named `.env` in the root of your project folder.

2. Add the following line to your `.env` file, replacing the credentials with your own:

```plaintext
# .env
DATABASE_URL="postgresql://YOUR_USERNAME:YOUR_PASSWORD@localhost:5432/civic_db"
```
*   **YOUR_USERNAME:** `postgres` (unless you created a new user)
*   **YOUR_PASSWORD:** The password you set during the Step 1 installation.
*   **localhost:5432:** This is the default address for a local PostgreSQL install.
*   **civic_db:** The name of the database you created in Step 2.


## 3. Running the Service
Your database is ready and your app is configured. Now, run the FastAPI server:

```python
# This will start the server, which will reload automatically when you save code
fastapi run user_management/main.py --reload --port {port} 
```