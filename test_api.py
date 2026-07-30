import requests

API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual key

response = requests.post(
    "http://localhost:8000/chat",
    headers={
        "X-API-Key": "awvJVdB9T_RAcXOzT47WPhgPPssgH7Hjf49eVjXNVtM",
        "Content-Type": "application/json"
    },
    json={
        "email": "test@example.com",
        "message": "What is your refund policy?"
    }
)

print(response.status_code)
print(response.json())