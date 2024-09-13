import requests
import json
print("HTTP Response:")
url_relay = 'http://18.189.225.139'
payload = {'API': 'test', 'instrument': 'test', 'Timestamp': 0, 'Data': {'relay': True, 'site': 'test'}}
response = requests.post(url_relay, json.dumps(payload), timeout=10)
print(response.status_code)