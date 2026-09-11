import requests

for page in [1, 2]:
    url = f"http://127.0.0.1:8000/api/events?page={page}&per_page=10"
    r = requests.get(url, timeout=30).json()
    print(f"page {page}: {len(r['items'])} items | total={r['total']} | has_more={r['has_more']} | next_page={r['next_page']}")
    print(f"  first event: {r['items'][0]['event_id']} at {r['items'][0]['updated_at']}")
    print(f"  last event:  {r['items'][-1]['event_id']} at {r['items'][-1]['updated_at']}")
