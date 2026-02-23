import json
import urllib.parse
import urllib.request
import re

def lambda_handler(event, context):
    """
    Bedrock Agent Web Search Tool.
    Uses DuckDuckGo (lite) to find adverse media results.
    """
    # VERBOSE LOGGING FOR DEBUGGING
    print(f"EVENT RECEIVED: {json.dumps(event)}")
    
    agent = event.get('agent')
    action_group = event.get('actionGroup')
    function = event.get('function')
    parameters = event.get('parameters', [])

    # Extract the search query from parameters safely
    search_query = ""
    if isinstance(parameters, list):
        for param in parameters:
            if isinstance(param, dict) and param.get('name') == 'query':
                search_query = param.get('value')
    
    if not search_query:
        print("Error: No search query found in parameters.")
        return _format_response(event, "No search query provided.", 400)

    # --- MOCK MODE LOGIC ---
    MOCK_RESULTS = {
        "Prigozhin": {
            "negative_news_found": True,
            "news_summary": "Yevgeny Prigozhin identified as a sanctioned individual. Reports link him to the Wagner Group and multiple allegations of money laundering and transnational crime.",
            "source_url": "https://test-compliance.kinetix/wagner-report"
        },
        "Fridman": {
            "negative_news_found": True,
            "news_summary": "Mikhail Fridman is a sanctioned oligarch. Web records show multiple fraud investigations and links to money laundering activities in Europe.",
            "source_url": "https://test-compliance.kinetix/alfabank-fraud"
        },
        "Saab": {
            "negative_news_found": True,
            "news_summary": "Alex Saab reported as a key financial proxy for the PDVSA regime. Investigations into massive money laundering schemes through shell companies.",
            "source_url": "https://test-compliance.kinetix/saab-pdvsa-case"
        },
        "Wagner": {
            "negative_news_found": True,
            "news_summary": "Wagner Shield Corp identified as a shell entity for the sanctioned Wagner Group. Associated with high-risk paramilitary activities.",
            "source_url": "https://test-compliance.kinetix/wagner-group-overview"
        },
        "Evergreen": {
            "negative_news_found": True,
            "news_summary": "Evergreen Financial Group (Simulation Match). System found simulated records indicating potential 'Shell Company' behavior in high-risk jurisdictions. Recommended for enhanced verification.",
            "source_url": "https://test-compliance.kinetix/simulation-evergreen-report"
        }
    }

    query_lower = str(search_query).lower()
    for key, mock_data in MOCK_RESULTS.items():
        if key.lower() in query_lower:
            print(f"Mock match found for {key}. Returning test results.")
            return _format_response(event, mock_data, 200)

    print(f"Live search for: {search_query}")
    
    try:
        encoded_query = urllib.parse.quote(str(search_query) + " fraud money laundering crime news")
        url = f"https://duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode('utf-8')
        
        snippets = re.findall(r'<a class="result__snippet" href=".*?">(.*?)</a>', html, re.DOTALL)
        
        if not snippets:
            return _format_response(event, "No adverse media found for this query.", 200)

        results_text = "\n".join([re.sub(r'<.*?>', '', s.strip()) for s in snippets[:3]])
        
        response_body = {
            "negative_news_found": len(results_text) > 20,
            "news_summary": results_text,
            "source_url": f"https://duckduckgo.com/?q={encoded_query}"
        }
        
        return _format_response(event, response_body, 200)

    except Exception as e:
        print(f"Error during search execution: {e}")
        return _format_response(event, f"Search infrastructure error: {str(e)}", 500)

def _format_response(event, body, status_code):
    """Formats the response according to Amazon Bedrock 1.0 Specification with high reliability."""
    try:
        # If body is a dict, convert to JSON string. If already string, keep as is.
        response_text = json.dumps(body) if isinstance(body, (dict, list)) else str(body)
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'UnknownGroup'),
                'function': event.get('function', 'UnknownFunction'),
                'functionResponse': {
                    'httpStatusCode': status_code,
                    'responseBody': {
                        'TEXT': {
                            'body': response_text
                        }
                    }
                }
            }
        }
    except Exception as format_err:
        print(f"CRITICAL: Failed to format response: {format_err}")
        # absolute fallback
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'error',
                'function': 'error',
                'functionResponse': {
                    'httpStatusCode': 500,
                    'responseBody': { 'TEXT': { 'body': 'Internal formatting error' } }
                }
            }
        }
