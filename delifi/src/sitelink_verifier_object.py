from urllib.request import urlopen
from urllib.parse import urlencode, unquote
from datetime import datetime
import json
import time
import sys

'''
False positives can happen. Known situations are:
- page has been moved after the dump was created  (dump:leads to a redirect, wikidata:right, wikipedia:right, sparql:right)
- page was created after the dump was created     (dump:missing, wikidata:right, wikipedia:right, sparql:right)
- the Wikidata query server might return old data (dump:right, wikidata:right, wikipedia:right, sparql:wrong)
'''


class Concept(object):

    def __init__(self, qid, title):
        self.qid = qid
        self.title = title
        self.page_creation_date = None

# TODO: Hoitamaton väärä positiivinen: sivu luotu dumpin luomisen jälkeen

# TODO: Väärä positiivinen: Wikipediassa on artikkeli ja Wikidatassa on linkki siihen,
# mutta Wikipedian mukaan linkkiä ei ole olemassa.
# Ei pitäisi tapahtua ellei Wikimedian tietokannoissa ole ongelmaa.

class Verifier(object):

    def __init__(self, result_dict, lang, date):
        self.object_list = []
        self.dict_to_object_list(dump)
        self.lang = lang
        self.dump_creation_date = date
        #self.false_positive_counter = 0


    def dict_to_object_list(self, dump):
        for i, qid in enumerate(dump):
            concept = Concept(qid, dump[qid])
            self.object_list.append(concept)


    def search_false_positives_old(self):
        qids = []
        labels = []
        wd_results = []
        wp_results = []
        false_positives = []
        print(len(self.object_list))

        

        if len(qids) == 50 or i == (len(self.object_list) - 1):
            wd_results = self.query_wikidata_api(qids)
            qids = []
            time.sleep(3)
            false_positives += self.parse_qids(wd_results)
        if len(labels) == 50 or i == (len(self.object_list) - 1):
            #print('Q6613346', data['Q6613346'])
            wp_results = self.query_wikipedia_api(labels)
            print(wp_results)
            labels = []
            time.sleep(3)
            false_positives += self.parse_labels(wp_results)
            print('Processed:', i + 1)
            sys.exit()

        '''
        for i, qid in enumerate(self.dump):
            qids.append(qid)
            labels.append(self.dump[qid])
            if len(qids) == 50 or i == (len(self.dump) - 1):
                wd_results = self.query_wikidata_api(qids)
                qids = []
                time.sleep(3)
                false_positives += self.parse_qids(wd_results)
            if len(labels) == 50 or i == (len(self.dump) - 1):
                #print('Q6613346', data['Q6613346'])
                wp_results = self.query_wikipedia_api(labels)
                print(wp_results)
                labels = []
                time.sleep(3)
                false_positives += self.parse_labels(wp_results)
                print('Processed:', i + 1)
                sys.exit()
        '''
        return false_positives  # False positives


    def query_wikidata_api(self, qids_to_query):
        # Example 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q42|Q33&props=sitelinks&sitefilter=enwiki'
        api_url = 'https://www.wikidata.org/w/api.php'
        print('Querying', api_url)
        data = {"action": "wbgetentities", "props": "sitelinks",
                "sitefilter":  self.lang + "wiki", "format": "json",
                "ids": '|'.join(qids_to_query)}
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res


    def query_wikipedia_api(self, labels):
        api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        print('Querying', api_url)
        data = {"action": "query", "prop": "pageprops",  # , "prop": "revisions"
                "format": "json", "titles": '|'.join(labels) }
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res


    def parse_qids(self, results):
        # TODO: Pitäisikö tuloksia verrata SPARQL-kyselyn tuloksiin??
        false_positives = []
        for qid in list(results["entities"]):
            tmp = results["entities"][qid]
            try:
                tmp["sitelinks"][self.lang + "wiki"]
            except KeyError:  # Sitelink already deleted
                false_positives.append(qid)
                continue
            if self.dump[qid] != tmp["sitelinks"][self.lang + "wiki"]["title"]:
                false_positives.append(qid)
        return false_positives


    def parse_date(self, date_str):
        # '2020-10-03T09:50:51Z'
        (date, time) = date_str[:-1].split('T')
        (year, month, day) = date.split('-')
        (hour, minute, second) = time.split(':')
        return datetime.datetime(year, month, day, hour, minute, second)


    def find_false_positives(self, one_result, qid):
        try:
            print('Wikipedia article doesn\'t have a Wikidata link', one_result, qid)
        except UnboundLocalError:
            print('Wikipedia article doesn\'t have a Wikidata link', one_result, 'unknown QID')

            # TODO: Get the page creation date, and compare it to the patch creation date.
            # https://sv.wikipedia.org/w/api.php?action=query&prop=revisions&rvlimit=1&rvprop=timestamp&rvdir=newer&titles=Mall:Folkmusik%20fr%C3%A5n%20H%C3%A4lsingland
            print(one_result["title"])
            res = self.query_revisions_from_wikipedia_api(one_result["title"])
            print(res)
            pid = list(res["query"]["pages"])[0]
            res["query"]["pages"][pid]['revisions'][0]["timestamp"]
            page_creation_date = self.parse_date(date_str)
            if self.dump_creation_date < page_creation_date:
                # Possible false positive: Page was created after the dump. Ignoring.
                return True
            return False


    def parse_labels(self, results):
        false_positives = []
        for id in list(results["query"]["pages"]):
            try:
                results["query"]["pages"][id]["missing"]
            except KeyError:
                try:
                    qid = results["query"]["pages"][id]["pageprops"]["wikibase_item"]
                    false_positives.append(qid)
                except KeyError:
                    if self.find_false_positives(results["query"]["pages"][id], qid):
                        #false_positives.append() # Doesn't have qid attached.
                        pass

                    continue
        return false_positives


    def query_revisions_from_wikipedia_api(self, title):
        # https://sv.wikipedia.org/w/api.php?action=query&prop=revisions&rvlimit=1&rvprop=timestamp&rvdir=newer&titles=titles&format=json
        api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        print('Querying', api_url)
        data = {"action": "query", "prop": "revisions", "rvlimit": "1",
                "rvprop": "timestamp", "rvdir": "newer",
                "format": "json", "titles": title }
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res


    # TODO: This should be made in object-oriented way.

    def search_false_positives_old(self):
        qids = []
        labels = []
        wd_results = []
        wp_results = []
        false_positives = []
        print(len(self.dump))

        for i, qid in enumerate(self.dump):
            qids.append(qid)
            labels.append(self.dump[qid])
            if len(qids) == 50 or i == (len(self.dump) - 1):
                wd_results = self.query_wikidata_api(qids)
                qids = []
                time.sleep(3)
                false_positives += self.parse_qids(wd_results)
            if len(labels) == 50 or i == (len(self.dump) - 1):
                #print('Q6613346', data['Q6613346'])
                wp_results = self.query_wikipedia_api(labels)
                print(wp_results)
                labels = []
                time.sleep(3)
                false_positives += self.parse_labels(wp_results)
                print('Processed:', i + 1)
                sys.exit()

        return false_positives  # False positives


if __name__ == '__main__':
    with open('tmp_out.json', 'r') as infile:
        data = json.load(infile)

    print('Q6613346', data['Q6613346'])

    verifier = Verifier(data, "en")
    false_positives = verifier.run_verification_queries()
    print(false_positives)
    print(len(false_positives))
