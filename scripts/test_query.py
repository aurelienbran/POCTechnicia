import requests
import json

def test_query(question: str):
    url = "http://localhost:8000/api/v1/query"
    headers = {"Content-Type": "application/json"}
    data = {
        "question": question,
        "k": 4
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    print("\nQuestion:", result.get("question"))
    print("\nRéponse:", result.get("answer"))
    print("\nSources:", json.dumps(result.get("sources", []), indent=2, ensure_ascii=False))
    print("\nTemps de traitement:", result.get("processing_time"))

if __name__ == "__main__":
    test_query("Expliquez les procédures de dépannage du système de démarrage et les spécifications techniques associées.")
