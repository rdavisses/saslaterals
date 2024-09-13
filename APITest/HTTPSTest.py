import requests
import json
print("HTTPS Response")
url = 'https://api.fenceline.info/v2/'
payload = {'API': 'test', 'instrument': 'test', 'Timestamp': 0, 'Data': {'relay': False, 'site': 'test'}}
response = requests.post(url_relay, json.dumps(payload), timeout=10)
print(response.status_code)