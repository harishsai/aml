import json
from aws_lambda_search import lambda_handler

def test_evergreen_match():
    print("\n--- Testing Evergreen Simulation Match ---")
    mock_event = {
        "agent": "AML-Orchestrator",
        "actionGroup": "WebSearchGroup",
        "function": "web_search",
        "parameters": [
            {
                "name": "query",
                "value": "Evergreen Financial Group"
            }
        ]
    }
    
    response = lambda_handler(mock_event, None)
    print("Response Format Check:")
    print(json.dumps(response, indent=2))
    
    # Assertions
    assert response['messageVersion'] == '1.0'
    assert 'response' in response
    assert 'functionResponse' in response['response']
    
    body = json.loads(response['response']['functionResponse']['responseBody']['TEXT']['body'])
    assert body['negative_news_found'] is True
    assert "Evergreen Financial Group (Simulation Match)" in body['news_summary']
    print("✅ Evergreen Match Test Passed!")

def test_live_search_fallback():
    print("\n--- Testing Live Search Fallback (Syntax Check) ---")
    mock_event = {
        "agent": "AML-Orchestrator",
        "actionGroup": "WebSearchGroup",
        "function": "web_search",
        "parameters": [
            {
                "name": "query",
                "value": "Random Company Name 12345"
            }
        ]
    }
    
    response = lambda_handler(mock_event, None)
    print("Response Received.")
    assert response['messageVersion'] == '1.0'
    print("✅ Live Search Syntax Test Passed!")

if __name__ == "__main__":
    try:
        test_evergreen_match()
        test_live_search_fallback()
        print("\n🏆 ALL HEALTH CHECKS PASSED!")
    except Exception as e:
        print(f"\n❌ HEALTH CHECK FAILED: {e}")
