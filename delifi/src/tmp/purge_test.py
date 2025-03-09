from urllib.request import urlopen, Request
from urllib.parse import urlencode, unquote
import json
import sys
import time

def purge_page(title):
    # https://www.mediawiki.org/wiki/API:Purge
    api_url = 'https://de.wikipedia.org/w/api.php'
    if type(title) == str:
        titles = title
    elif type(title) == list:
        titles = '|'.join(title)

    data = {
        "action": "purge",
        "titles": titles,
        "format": "json"
        }
    req = Request(api_url, data=urlencode(data).encode())
    print(urlencode(data).encode())
    raw = urlopen(req).read()
    res = json.loads(raw)
    return res


print(purge_page(['Wikipedia:Spielwiese']))
time.sleep(1)
print(purge_page('Wikipedia:Spielwiese'))
