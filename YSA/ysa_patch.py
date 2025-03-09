from qsfilemaker import QSLine, WDID
import rdflib
import json
import requests

'''
skos:note
dc:source
skos:definition
'''


YSA_PREFIX = 'http://www.yso.fi/onto/ysa/'
WD_PREFIX = 'http://www.wikidata.org/entity/'
PREF_LABEL = 'http://www.w3.org/2004/02/skos/core#prefLabel'

#jsonfile = 'query_programming_languages_20190114.json'
jsonfile = 'query_kansat_20190115.json'
jsonfile = 'query_koirarodut_20190115.json'
jsonfile = 'query_kansallispuistot_20190115.json'
jsonfile = 'query_kartanot_20190116.json'
id = 'Y97741'   # ohjelmointikielet
id = 'Y95886'   # kansat
id = 'Y96272'   # koirarodut
id = 'Y95847'   # kansallispuistot
id = 'Y95910'  # kartanot


def get_ysa_id(url):
    assert url.startswith(YSA_PREFIX)
    return url.split('/')[-1]

def get_wd_id(url):
    assert url.startswith(WD_PREFIX)
    return url.split('/')[-1]


with open(jsonfile, 'r') as infile:
    data = json.load(infile)

#g = rdflib.Graph()
#g.parse('ysa-skos.ttl', format='turtle')

g = rdflib.Graph()

def parse():
    #link = 'http://finto.fi/rest/v1/ysa/data?uri=http%3A%2F%2Fwww.yso.fi%2Fonto%2Fysa%2F' + id + '&format=application/ld%2Bjson'
    if id.startswith('Q'):
        print('ERROR. ID has incorrect format.')
        return
    link = 'http://finto.fi/rest/v1/ysa/data?uri=http%3A%2F%2Fwww.yso.fi%2Fonto%2Fysa%2F' + id + '&format=text/turtle'

    #print(r.text)
    g.parse(link, format='turtle')

    for s, p, o in g:
        if p.strip() != PREF_LABEL:
            continue
        for item in data:
            if item['fiLabel'].lower() == o.strip().lower():
                '''
                print(get_wd_id(item['item']))
                print(get_ysa_id(s))
                #print(p)
                print(o)
                print()
                '''
                line = QSLine(get_wd_id(item['item']))
                line.add_string_to_line('P6293', get_ysa_id(s))
                print(line.line)


#parse()
