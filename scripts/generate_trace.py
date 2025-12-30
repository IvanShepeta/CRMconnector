import requests

URLS = [
    "http://localhost:3001/mcp",
    "http://localhost:3001/",
]

if __name__ == '__main__':
    for url in URLS:
        try:
            resp = requests.get(url, timeout=5)
            print(f"GET {url} -> Status: {resp.status_code}")
            text_sample = resp.text[:400].replace('\n', ' ')
            if text_sample:
                print(text_sample)
        except Exception as e:
            print(f"GET {url} -> Error: {e}")
    print('\nMake sure the MCP Server is running on http://localhost:3001 and the AI Toolkit trace collector is open (`ai-mlstudio.tracing.open`) to view spans.')