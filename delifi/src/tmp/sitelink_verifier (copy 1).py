from urllib.request import urlopen
from urllib.parse import urlencode, unquote
from qsfilemaker import WDID
import json
import time
import sys
import urllib.parse

'''
False positives can happen. Known situations are:
- page has been moved after the dump was created  (dump:leads to a redirect, wikidata:right, wikipedia:right, sparql:right)
- page was created after the dump was created     (dump:missing, wikidata:right, wikipedia:right, sparql:right)
- the Wikidata query server might return old data (dump:right, wikidata:right, wikipedia:right, sparql:wrong)
'''

class Verifier(object):

    def __init__(self, result_dict, lang):
        self.dump = result_dict
        self.lang = lang
        self.input_filename = 'query.json'
        #self.false_positive_counter = 0

    def parse_json(self):
        counter = 0
        template_list = {}
        base_url = 'https://' + self.lang + '.wikipedia.org/wiki/'
        try:
            with open(self.input_filename, 'r') as infile:
                data = json.load(infile, encoding='utf-8')
        except FileNotFoundError:
            print('File:', self.input_filename, 'not found. Nothing was done.')
            sys.exit()
        for item in data:
            sitelink = urllib.parse.unquote(item['sitelink']).replace('_', ' ')
            if sitelink.startswith(base_url + 'Template:'):
                template_list[
                    WDID.get_qid(item['item'])
                    ] = sitelink.replace(base_url, '') #.encode('utf-8')
        return template_list

    '''
    def unescape_part(self, out, last_index):
        try:
            txt = html.unescape(out[last_index:].decode('utf-8'))
        except UnicodeDecodeError:
            txt = html.unescape(
                out[last_index:out.rindex(b'\n')].decode('utf-8'))
        return txt.encode('utf-8')
    '''

    def query_wikidata_api(self, qids_to_query):
        # Example 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q42|Q33&props=sitelinks&sitefilter=enwiki'
        api_url = 'https://www.wikidata.org/w/api.php'
        data = {"action": "wbgetentities", "props": "sitelinks",
                "sitefilter":  self.lang + "wiki", "format": "json",
                "ids": '|'.join(qids_to_query)}
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res

    def query_wikipedia_api(self, labels):
        api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        data = {"action": "query", "prop": "pageprops",  # , "prop": "revisions"
                "format": "json", "titles": '|'.join(labels) }
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res

    # TODO: Vertaa wd ja wp resultteja toisiinsa???!
    def parse_results(self, wd_results, wp_results, dump):
        pass

    def parse_qids(self, results, data):
        # TODO: Pitäisikö tuloksia verrata SPARQL-kyselyn tuloksiin??
        false_positives = []
        for qid in list(results["entities"]):
            tmp = results["entities"][qid]
            try:
                tmp["sitelinks"][self.lang + "wiki"]
            except KeyError:  # Sitelink already deleted
                #del data[qid]
                continue
            if data[qid] == tmp["sitelinks"][self.lang + "wiki"]["title"]:
                del data[qid]
            else:
                print(data[qid],
                    tmp["sitelinks"][self.lang + "wiki"]["title"])

    '''
    def parse_qids(self, results, data, sparql_data):
        # TODO: Pitäisikö tuloksia verrata SPARQL-kyselyn tuloksiin??
        for qid in list(results["entities"]):
            tmp = results["entities"][qid]
            try:
                tmp["sitelinks"][self.lang + "wiki"]
            except KeyError:  # Sitelink already deleted
                del data[qid]
                continue
            if sparql_data[qid] == tmp["sitelinks"][self.lang + "wiki"]["title"]:
                del data[qid]
            else:
                print(sparql_data[qid],
                    tmp["sitelinks"][self.lang + "wiki"]["title"])
    '''


    def parse_labels(self, results, data):
        for id in list(results["query"]["pages"]):
            try:
                results["query"]["pages"][id]["missing"]
            except KeyError:
                try:
                    qid = results["query"]["pages"][id]["pageprops"]["wikibase_item"]
                    print(qid, data[qid])
                    del data[qid]
                except KeyError:
                    continue
            '''
            try:
                results["query"]["pages"][id]["missing"]
            except KeyError:
                # Article is not missing. Delete these from here so they wont be deleted from WD.
                print('Not missing:', results["query"]["pages"][id]["title"])
                qid = results["query"]["pages"][id]["pageprops"]["wikibase_item"]

                # TODO: Ongelma-linkit päätyvät tänne, mutta niitä ei saa poistaa data-dictionarysta.
                # Jäljelle pitäisi jäädä vain false positive, joihin ongelma-linkit kuuluvat.
                try:
                    del data[qid]
                except KeyError:
                    print('KeyError:', qid)
                    return
            '''
            '''
            for qid in data:
                if data[qid] == results["query"]["pages"][id]["title"]:
                    del data[qid]
                    break
            '''
            '''
            for qid in self.dump:
                try:
                    data[qid]
                except KeyError:
                    continue
                if data[qid] == results["query"]["pages"][id]["title"]:
                    del data[qid]
                    break
            '''



    def run_verification_queries(self):
        qids = []
        labels = []
        wd_results = []
        wp_results = []
        data = self.dump.copy()
        print(len(data), len(self.dump))
        print('Q6613346', data['Q6613346'])
        sparql_data = self.parse_json()

        for i, qid in enumerate(self.dump):
            qids.append(qid)
            labels.append(self.dump[qid])
            if len(qids) == 50 or i == (len(self.dump) - 1):
                wd_results = self.query_wikidata_api(qids)
                time.sleep(3)
                self.parse_qids(wd_results, data, sparql_data)
                qids = []
            if len(labels) == 50 or i == (len(self.dump) - 1):
                #print('Q6613346', data['Q6613346'])
                wp_results = self.query_wikipedia_api(labels)
                time.sleep(3)
                self.parse_labels(wp_results, data)
                labels = []
                print('Processed:', i + 1)
        return data  # False positives


if __name__ == '__main__':
    with open('tmp_out.json', 'r') as infile:
        data = json.load(infile)

    print('Q6613346', data['Q6613346'])

    verifier = Verifier(data, "en")
    false_positives = verifier.run_verification_queries()
    print(false_positives)
    print(len(false_positives))
