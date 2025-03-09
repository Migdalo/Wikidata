from qsfilemaker import QSLine, WDID
from urllib.parse import quote_plus
from urllib.parse import unquote_plus
from SPARQLWrapper import SPARQLWrapper
import rdflib
import pprint
import json
import argparse
import time

'''
SELECT DISTINCT ?item ?fiLabel ?tLabel
WHERE
{
  ?item wdt:P17 wd:Q33 ;
        #wdt:P31/wdt:P279* wd:Q618123 ;
        wdt:P31/wdt:P279* wd:Q43229 ;
        wdt:P31 ?tyyppi ;
        rdfs:label ?fiLabel .
  ?tyyppi rdfs:label ?tLabel .
  FILTER(LANG(?tLabel) = 'fi')
  FILTER(LANG(?fiLabel) = 'fi')
  MINUS { ?item wdt:P31 wd:Q856076 . }
  MINUS { ?item wdt:P31 wd:Q17468533 . }
  MINUS { ?item wdt:P5266 [] . }
}
'''

vaihtoehtoinen_nimi = 'http://rdaregistry.info/Elements/a/P50025'
organisaatiotyyppi = 'http://rdaregistry.info/Elements/a/P50237'
nimi = 'http://rdaregistry.info/Elements/a/P50041'

'''
Encyclopaedia Metallum
Wikipedia
Discogs.com / Discogs
Elonet
VIAF
'''

skip = [
    "Q18690251", "Q11884751", "Q11740116", "Q20251899", "Q18680101",
    "Q18658729", "Q368117", "Q56398771", "Q18690373", "Q20254390",
    "Q11871734", "Q18688929"]

class FintoDataSet(object):
    # 'Elonet': Ei yhtiö-tunnisteita Wikidatassa
    #properties = {'Discogs': 'P1953', 'Encyclopaedia Metallum', 'VIAF': 'P214'}

    def __init__(self, finto_filename, wd_filename, wd_link, metallum_link):
        self.finto_data_filename = finto_filename
        self.wikidata_filename = wd_filename
        self.wikidata_link = wd_link
        self.metallum_link = metallum_link
        self.data = self.open_json_file()
        self.count = 0
        self.pid = 'P5266'

    def parse_source_line(self, line):
        # Discogs.com, katsottu 8.3.2016 https://www.discogs.com/artist/1053489-tak
        tmp = line.split(',')
        if len(tmp) == len(line):
            return None
        site = tmp[0]
        tmp = ''.join(tmp[1:]).split()
        try:
            if tmp[-1].startswith('http'):
                id = tmp[-1].split('/')[-1]
                if id:
                    return (site, id)
        except IndexError:
            return None
        return None

    def get_qid_from_wd(self, pid, id):
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        #pid = 'P214'
        #id = '140094734'
        #query = 'SELECT ?item WHERE { ?item wdt:' + pid + ' "' + id + '" }'
        query = 'SELECT ?item WHERE { ?item wdt:' + pid + ' "' + id +\
                '". FILTER NOT EXISTS { ?item wdt:P5266 [] } ' +\
                'FILTER NOT EXISTS { ?item wdt:P31 wd:Q5 } . }'
        sparql.setQuery(query)
        sparql.setReturnFormat('json')
        results = sparql.query().convert()
        #return WDID.get_validated_qid(
        #            results['results']['bindings'][0]['item']['value'])
        time.sleep(2)
        try:
            return results['results']['bindings'][0]['item']['value']
        except IndexError:
            return None


    def iterate_sources(self):
        sources = ['Encyclopaedia Metallum', 'Discogs', 'VIAF']
        count = 0
        sites = []
        g = rdflib.Graph()
        g.parse(self.finto_data_filename, format='turtle')
        start_time = time.time()
        for subject,predicate,obj in g:
            if predicate.strip() != 'http://purl.org/dc/elements/1.1/source':
                continue
            for source in obj.splitlines():
                try:
                    (site, id) = self.parse_source_line(source)
                except TypeError:
                    continue

                if 'VIAF' in site:
                    qid = self.get_qid_from_wd('P214', id)
                    if qid is None:
                        continue
                    #print(qid, site, id, subject)
                    line = QSLine(qid)
                    line.add_string_to_line('P5266', subject.split(':')[-1])
                    print(line.line)
                    count += 1

                elif 'Discogs' in site:
                    qid = self.get_qid_from_wd('P1953', id.split('-')[0])
                    if qid is None:
                        continue
                    #print(qid, site, id, subject)
                    line = QSLine(qid)
                    line.add_string_to_line('P5266', subject.split(':')[-1])
                    print(line.line)
                    count += 1

                elif 'Encyclopaedia Metallum' in site:
                    qid = self.get_qid_from_wd('P1952', id)
                    if qid is None:
                        continue
                    #print(qid, site, id, subject)
                    line = QSLine(qid)
                    line.add_string_to_line('P5266', subject.split(':')[-1])
                    print(line.line)
                    count += 1

        print(count)
        print(time.time() - start_time)


    def open_json_file(self):
        with open(self.wikidata_filename, 'r') as infile:
            data = json.load(infile)
        return data

    def parse(self, url):
        # http://urn.fi/URN:NBN:fi:au:cn:186834A
        return url.split(':')[-1]

    def get_wiki_url(self, line):
        val = line.split()[-1].strip()
        if val.startswith('https://'):
            return val
        else:
            return None

    def plink(self, url):
        tmp = url.split('/')
        return '/'.join(tmp[:-1]) + '/' + quote_plus(tmp[-1])

    def verify(self):
        results = []
        count = 0
        g = rdflib.Graph()
        g.parse(self.finto_data_filename, format='turtle')
        for item in self.data:
            objs = g.objects(
                rdflib.URIRef('http://urn.fi/URN:NBN:fi:au:cn:' + item['value']),
                rdflib.URIRef('http://purl.org/dc/elements/1.1/source'))

            for obj in objs:
                if 'Wikipedia' in obj.strip():
                    url = self.get_wiki_url(obj.strip())
                    if url is None:
                        continue
                    '''
                    if rdflib.URIRef(url) != rdflib.URIRef(
                            quote_plus(item['sitelinkfi'])):
                    '''
                    #if url != item['sitelinkfi']:
                    url = self.plink(unquote_plus(url))
                    if url != item['sitelinkfi']:
                        plink = self.plink(unquote_plus(item['sitelinkfi']))
                        if url != plink:
                            #print(url, item['sitelinkfi'], url == item['sitelinkfi'])
                            print(url, plink) # , url == plink

        '''
        for subject,predicate,obj in g:
            if predicate.strip() != 'http://purl.org/dc/elements/1.1/source':
                continue

            if self.wikidata_link and 'Wikipedia' in obj.strip():
                url = self.get_wiki_url(obj.strip())
                print(subject,predicate,obj)
        '''


    def print_results(self, results):
        qids = [line['item'] for line in results]
        subjects = [line['subject'] for line in results]
        i = 0
        for item in results:
            if qids.count(item['item']) > 1:
                continue
            if subjects.count(item['subject']) > 1:
                continue
            if WDID.get_validated_qid(item['item']) in skip:
                continue
            line = QSLine(item['item'])
            line.add_string_to_line(self.pid, item['subject'])
            print(line.line)
            i += 1
        print(i, '/', self.count)

    def parse_name(self, name):
        try:
            label, tarkenne = name.split('(')
            tarkenne = tarkenne.split(')')[0]
            return (label, tarkenne)
        except ValueError:
            return (name, None)

    def parse_metallium_url(url):
        url.split('Encyclopaedia Metallum')[1].splitlines()[0]

    def iterate(self):
        results = []
        g = rdflib.Graph()
        g.parse(self.finto_data_filename, format='turtle')
        for subject,predicate,obj in g:
            if self.wikidata_link:
                if predicate.strip() != 'http://purl.org/dc/elements/1.1/source':
                    continue
                if 'Wikipedia' in obj.strip():
                    url = self.get_wiki_url(obj.strip())
                    if url is None:
                        continue
                    for item in self.data:
                        try:
                            if url == item['sitelinkfi']:
                                line = {}
                                line['item'] = item['item']
                                line['subject'] = self.parse(subject)
                                self.count += 1
                                results.append(line)
                        except KeyError:
                            pass
            elif self.metallum_link:
                if predicate.strip() != 'http://purl.org/dc/elements/1.1/source':
                    continue
                if 'Encyclopaedia Metallum' in obj.strip():
                    url = self.get_wiki_url(obj.strip())
                    if url is None:
                        continue
                    for item in self.data:
                        try:
                            if url == item['metallum']:
                                line = {}
                                line['item'] = item['item']
                                line['subject'] = self.parse(subject)
                                self.count += 1
                                results.append(line)
                        except KeyError:
                            pass
            else:
                parsed_name, tarkenne = self.parse_name(nimi)
                if predicate.strip().lower() == parsed_name.strip().lower():
                    for item in self.data:
                        '''
                        try:
                            if 'kunta' in item['tLabel']:
                                continue
                            if 'kaupunki' in item['tLabel']:
                                continue
                        except KeyError:
                            continue
                        '''
                        if item['fiLabel'].lower().strip() == obj.lower().strip():
                            line = {}
                            line['item'] = item['item']
                            line['subject'] = self.parse(subject)
                            self.count += 1
                            results.append(line)

        self.print_results(results)

# TODO: Vertaa nimiä ilman suluissa olevaa tarkennetta
# TODO: SPARQL query against Wikidata for all items having 'P5266' value
# TODO: Check QS list for values already in Wikidata in some other item.

# 'query_organizations.json'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verify', default=False, action='store_true',
                        help='Verify validity of existing statements.')
    parser.add_argument('-s', '--sources', default=False, action='store_true',
                        help='Iterate sources.')
    parser.add_argument('-w', '--wikipedia', default=False, action='store_true',
                        help='List elements that have' +
                        'Wikipedia marked as the source.')
    parser.add_argument('-m', '--metallum', default=False, action='store_true',
                        help='List elements that have' +
                        'Encyclopaedia Metallum marked as the source.')
    args = parser.parse_args()
    #iterate('ysa-skos.ttl')
    ds = FintoDataSet(
        'cn-skos.ttl', 'organisations_12122018_2.json',
        args.wikipedia, args.metallum)
    if args.sources:
        ds.iterate_sources()
    elif args.verify:
        ds.verify()
    else:
        ds.iterate()
    #iterate('cn-skos.ttl', data, args.source)
