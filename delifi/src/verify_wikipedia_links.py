from urllib.request import urlopen
from urllib.parse import urlencode, unquote
import json
import time


def query_wikipedia_api(labels, lang):
    # Ecample 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q42|Q33&props=sitelinks&sitefilter=enwiki'
    api_url = 'https://' + lang + '.wikipedia.org/w/api.php'
    data = {"action": "query",  # , "prop": "revisions"
            "format": "json", "titles": '|'.join(labels) }
    raw = urlopen(api_url, urlencode(data).encode()).read()
    res = json.loads(raw)
    return res


with open('tmp_out.json', 'r') as infile:
    data = json.load(infile)


labels = []
results_sets = []
for i, label in enumerate(data):
    labels.append(data[label])
    if len(labels) == 50 or i == (len(data) - 1):
        results_sets.append(query_wikipedia_api(labels, 'en'))
        labels = []
        time.sleep(5)
    #print(qid, data[qid])


#print(results_sets[0])
false_positive_counter = 0
for results in results_sets:
    for id in list(results["query"]["pages"]):
        try:
            results["query"]["pages"][id]["missing"]
        except KeyError:
            # Article is not missing. These links should not be deleted.
            print(results["query"]["pages"][id]["title"])
            false_positive_counter += 1

print('Found false positives:', false_positive_counter)
