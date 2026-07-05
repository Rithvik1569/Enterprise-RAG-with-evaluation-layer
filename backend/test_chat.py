import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def main():
    print("Testing the RAG Chat Endpoint...\n")
    
    # 1. Register or Login
    credentials = {"email": "testuser_fresh@example.com", "username": "testuser_fresh", "password": "password123"}
    
    print(f"Registering user: {credentials['email']}")
    reg_response = requests.post(f"{BASE_URL}/auth/register", json=credentials)
    
    if reg_response.status_code == 201:
        token = reg_response.json()["access_token"]
        print("Registration successful.")
    elif reg_response.status_code == 409:
        print("User already exists, logging in...")
        login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
        if login_res.status_code == 200:
            token = login_res.json()["access_token"]
            print("Login successful.")
        else:
            print("Login failed:", login_res.text)
            sys.exit(1)
    else:
        print("Registration failed:", reg_response.text)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Ask a Question
    question = "What is the purpose of this RAG system?"
    print(f"\nAsking Question: '{question}'")
    
    chat_payload = {
        "message": question,
        "top_k": 4
    }
    
    chat_res = requests.post(f"{BASE_URL}/chat", json=chat_payload, headers=headers)
    
    if chat_res.status_code == 200:
        data = chat_res.json()
        print("\n=== RESPONSE ===")
        print(data.get("answer", "No answer provided"))
        print("\n=== EVALUATION METRICS ===")
        eval_metrics = data.get("evaluation")
        if eval_metrics:
            for k, v in eval_metrics.items():
                print(f"{k}: {v}")
        else:
            print("No evaluation metrics returned.")
        print(f"\nResponse Time: {data.get('response_time')}s")
    else:
        print("Chat request failed:", chat_res.text)

if __name__ == "__main__":
    main()
