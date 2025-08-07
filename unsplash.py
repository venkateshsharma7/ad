import requests

UNSPLASH_ACCESS_KEY = 'PAqKqdFq2W9KgIu04skiiNGE4XWRkNCJHrYWqHStYMg'  # <-- put your real key here!

def test_unsplash():
    url = 'https://api.unsplash.com/photos/random'
    params = {
        'query': 'food',
        'client_id': UNSPLASH_ACCESS_KEY,
        'orientation': 'landscape'
    }
    try:
        resp = requests.get(url, params=params, timeout=7)
        print('Status code:', resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print('Image URL:', data['urls']['regular'])
        else:
            print('Error response:', resp.text)
    except Exception as e:
        print('Exception:', e)

test_unsplash()