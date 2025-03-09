from urllib.request import urlopen
from urllib.parse import urlencode, unquote
import json
import time

def query_wikidata_api(qids_to_query):
    # Ecample 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q42|Q33&props=sitelinks&sitefilter=enwiki'
    api_url = 'https://www.wikidata.org/w/api.php'
    data = {"action": "wbgetentities", "props": "sitelinks",
            "sitefilter": "enwiki", "format": "json",
            "ids": '|'.join(qids_to_query)}
    raw = urlopen(api_url, urlencode(data).encode()).read()
    res = json.loads(raw)
    return res
    #return self.query_wikimedia_api(query)

with open('tmp_out.json', 'r') as infile:
    data = json.load(infile)

qids = []
#results = []
data_copy = data.copy()
print(len(data_copy))

for i, qid in enumerate(data):
    qids.append(qid)
    if len(qids) == 50 or i == (len(data) - 1):
        results = query_wikidata_api(qids)
        qids = []
        time.sleep(2)
        for qid in list(results["entities"]):
            try:
                results["entities"][qid]["sitelinks"]["enwiki"]
            except KeyError:  # Sitelink already deleted
                continue
            if data_copy[qid] == results["entities"][qid]["sitelinks"]["enwiki"]["title"]:
                del data_copy[qid]
            else:
                print(data_copy[qid], results["entities"][qid]["sitelinks"]["enwiki"]["title"],
                      data_copy[qid] == results["entities"][qid]["sitelinks"]["enwiki"]["title"])
        print('Processed counter:', i + 1)

print(data_copy)
print(len(data_copy))
