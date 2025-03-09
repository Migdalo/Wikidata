from urllib.request import urlopen
from urllib.parse import urlencode, unquote
import json
import time



if __name__ == '__main__':
    # https://de.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=namespaces
    lang = 'vec'
    api_url = 'https://' + lang + '.wikipedia.org/w/api.php'
    data = {"action": "query",  # , "prop": "revisions"
            "format": "json", "meta": "siteinfo", "siprop": "namespaces" }
    raw = urlopen(api_url, urlencode(data).encode()).read()
    res = json.loads(raw)
    print(res['query']['namespaces']["10"]['*'])
