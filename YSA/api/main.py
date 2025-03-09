from bs4 import BeautifulSoup
from SPARQLWrapper import SPARQLWrapper
import requests


class YSA(object):
    def __init__(self):
        self.url = 'http://finto.fi/cn/fi/'
        self.filepath = None

    def get_last_update(self):
        r = requests.get(self.url)
        print(r)
        print(r.text)

    def get_subject(self, id):


o = YSA()
#o.get_last_update()

def query_wikidata():
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    pid = 'P214'
    id = '140094734'
    query = 'SELECT ?item WHERE { ?item wdt:' + pid + ' "' + id + '" }'
    sparql.setQuery(query)
    sparql.setReturnFormat('json')
    results = sparql.query().convert()
    print(results['results']['bindings'][0]['item']['value'])
