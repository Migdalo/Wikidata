from urllib.parse import urlencode, unquote, quote_plus
from urllib.error import HTTPError
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointNotFound, EndPointInternalError
from json.decoder import JSONDecodeError
import json
import sys
import time
#import requests
#import urllib.parse

# TODO: Handle Retry-After header
# 429 (or 403)

def query_sparqlwrapper(url, query):
    sparql = SPARQLWrapper(url + "sparql", agent='DeletedSitelinkHunt')
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    retry_counter = 0
    while True:
        try:  # TODO: Error handling
            results = sparql.query()
            break
        except HTTPError:
            if retry_counter == 5:
                print('Failed to query Wikidata SPARQL end point. Aborting.')
                break
            print('Failed to query Wikidata SPARQL end point. Retrying.')
            retry_counter += 1
            time.sleep(5)
        except EndPointInternalError:
            print('Failed to query Wikidata SPARQL end point. Aborting.')
            break
    '''
    print(len(results.response.read()))  # <-- .read() consumes the results
    if len(results.response.read()) == 0:
        print('Failed to retreive any results.')
        return None
    '''
    try:
        ret = results.convert()
    except JSONDecodeError:
        ret = json.loads(results.response.read(), encoding='utf-8')
        #print('JSONDecodeError')
    '''
    except IncompleteRead:
        print("IncompleteRead error. Retrying.")
        time.sleep(5)
        query_sparqlwrapper(url, query)  # Risk of infinite loop!!
    '''
    return ret

'''
def query_sparql(url, query, header):
    r = requests.get(url + urllib.parse.quote(query) + '&format=json', headers=header) #  + '#'
    return r.text

def query_wikidata2(query):
    url = 'https://query.wikidata.org/sparql?query='
    headers = {'Accept': 'application/sparql-results+json'}
    return query_sparql(url, query, headers)

def get_qid(url):
    return url.split('/')[-1]
'''

def query_wikidata(query, output_filename='test.json'):
    url = 'https://query.wikidata.org/'
    if not query:
        with open('./queries/get_disambiguation_pages.sprql', 'r') as infile:
            query = infile.read().strip()
    try:
        results = query_sparqlwrapper(url, query)
    except UnboundLocalError:
        print('UnboundLocalError');
        return None
    except JSONDecodeError:
        print('Failed to query SPARQL server.')
        return None
    labels = results["head"]["vars"]
    output = []
    #print(results['results']['bindings'])
    for result in results['results']['bindings']:
        # 7.11.2020 Added .decode('utf-8') x2 here
        item = {'item': result[labels[0]]['value'],  # str has no .decode('utf-8')
                #'site': result[labels[1]]['value'],
                'sitelink': result[labels[1]]['value'] }  # .decode('utf-8')
        output.append(item)

    with open(output_filename, 'w') as out:
        json.dump(output, out)
