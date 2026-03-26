import requests

def test_get_request():
    response = requests.get('https://httpbin.org/get')
    assert response.status_code == 200
    assert 'url' in response.json()

def test_post_request():
    payload = {'key': 'value'}
    response = requests.post('https://httpbin.org/post', json=payload)
    assert response.status_code == 200
    assert response.json()['json'] == payload