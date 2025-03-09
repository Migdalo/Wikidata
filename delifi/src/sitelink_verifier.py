from urllib.request import urlopen, Request
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


# TODO: Hoitamaton väärä positiivinen: sivu luotu dumpin luomisen jälkeen

# TODO: Väärä positiivinen: Wikipediassa on artikkeli ja Wikidatassa on linkki siihen,
# mutta Wikipedian mukaan linkkiä ei ole olemassa.
# Ei pitäisi tapahtua ellei Wikimedian tietokannoissa ole ongelmaa.

class Verifier(object):

    def __init__(self, result_dict, lang, date):
        self.dump = result_dict
        self.lang = lang
        self.dump_creation_date = date
        self.api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        self.needs_purging = []
        self.false_positives = []
        #self.false_positive_counter = 0


    '''
    Function recieves a list of qids, and queries Wikidata to find out
    if the qids exists.
    '''
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

    '''
    Function recieves a list of labels, and queries a Wikipedia to find out
    if the articles with those labels exists.
    '''
    def query_wikipedia_api(self, labels):
        #api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        print('Querying', self.api_url)
        data = {"action": "query", "prop": "pageprops",  # , "prop": "revisions"
                "format": "json", "titles": '|'.join(labels) }
        raw = urlopen(self.api_url, urlencode(data).encode() + b"&redirects").read()
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
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))

    '''
    def find_false_positives(self, one_result, qid):
        try:
            print('Wikipedia article doesn\'t have a Wikidata link', one_result, qid)
        except UnboundLocalError:
            print('Wikipedia article doesn\'t have a Wikidata link', one_result, 'unknown QID')

            # TODO: Get the page creation date, and compare it to the patch creation date.
            # https://sv.wikipedia.org/w/api.php?action=query&prop=revisions&rvlimit=1&rvprop=timestamp&rvdir=newer&titles=Mall:Folkmusik%20fr%C3%A5n%20H%C3%A4lsingland
            print(one_result["title"])
            res = self.query_revisions_from_wikipedia_api(one_result["title"])
            #print(res)
            pid = list(res["query"]["pages"])[0]
            res["query"]["pages"][pid]['revisions'][0]["timestamp"]
            page_creation_date = self.parse_date(date_str)
            if self.dump_creation_date < page_creation_date:
                # Possible false positive: Page was created after the dump. Ignoring.
                return True
            return False
    '''

    def purge_page(self, title):
        # https://www.mediawiki.org/wiki/API:Purge
        #api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        if type(title) == str:
            titles = title
        elif type(title) == list:
            titles = '|'.join(title)
        data = {
            "action": "purge",
            "titles": '|'.join(title),
            "format": "json"
            }
        req = Request(self.api_url, data=urlencode(data).encode())
        #print(urlencode(data).encode())
        raw = urlopen(req).read()
        res = json.loads(raw)
        return res


    def compare_creation_dates(self, id, results):
        res = self.query_revisions_from_wikipedia_api(results["query"]["pages"][id]['title'])
        time.sleep(1)
        try:
            res['query']['pages'][id]['revisions']
        except KeyError:
            print('!!!!Error: ', res['query']['pages'][id])
            return None
        if self.dump_creation_date < self.parse_date(res['query']['pages'][id]['revisions'][0]['timestamp']):
            for key in self.dump.keys():
                #print('***', self.dump[key], results["query"]["pages"][id]['title'])
                if self.dump[key] == results["query"]["pages"][id]['title']:
                    #false_positives.append(key)
                    #break
                    return key
        return None


    def process_normalized_titles(self, normalized):
        # TODO: Handle normalized page titles
        # Skip all sitelinks that were normalized. This is a temporary solution!
        '''
        "normalized": [
            {
                "from": "Mod\u00e8l:Bo",
                "to": "Mode\u0142o:Bo"
            },
            {
                "from": "Mod\u00e8l: 1",
                "to": "Mode\u0142o:1"
            }
        ]
        '''
        false_positive_label = []
        false_positives = []
        for i in range(len(normalized)):
            print('Page title is normalized from', normalized[i]["from"],
                    'to', normalized[i]["to"])
            for qid in self.dump.keys():
                # TODO: Qid shouldn't be compared to titles,
                # they should be compared to other qids.
                print(self.dump[qid], normalized[i]["from"])
                if self.dump[qid] == normalized[i]["from"]:
                    false_positives.append(qid)
                    break
        # Subcase 1: to-page is linked to Wikidata
        # Subcase 2: to-page isn't linked to Wikidata

        '''
        for title in false_positive_label:
            for qid in self.dump.keys():
                if self.dump[qid] == title:
                    false_positives.append(qid)
                    break
        '''
        return false_positives


    def parse_labels(self, results):
        self.needs_purging = []
        false_positives = []
        false_positive_label = []

        # TODO: Normalisointi ei toimi?
        try:
            false_positives.append(
                self.process_normalized_titles(results["query"]["normalized"]))
        except KeyError:
            pass


        # TODO: Redirects?

        '''
        try:
            #for i in range(len(results["query"]["redirects"])):
            results["query"]["redirects"][0]
            try:
                with open('redirects.log', 'r') as infile:
                    log = json.load(infile)
            except json.decoder.JSONDecodeError:
                log = []
            log.append(results["query"])
            print(log)
            with open('redirects.log', 'w+') as outfile:
                json.dump(outfile, log)
            #sys.exit()
        except KeyError:
            pass
        '''

        #TODO: False_positives are still processed in the for loop below.

        for id in list(results["query"]["pages"]):
            #print(id)

            # Found a missing page.
            try:
                results["query"]["pages"][id]["missing"]
                continue
            except KeyError:
                pass


            # Found an existing page. This is a false positive.
            try:
                #print(results["query"]["pages"][id]['title'])
                qid = results["query"]["pages"][id]["pageprops"]["wikibase_item"]
                #print(qid, self.dump[qid])
                false_positives.append(qid)
                continue
            except KeyError:
                pass


            #print(results["query"]["pages"][id]['ns'] )
            '''
            if results["query"]["pages"][id]['ns'] != 10:  # Non template namespace
                #false_positive_label.append(results["query"]["pages"][id]['title'])
                for qid in self.dump.keys():
                    if self.dump[qid] == results["query"]["pages"][id]['title']:
                        false_positives.append(qid)
                        break
            '''

            # Skipping items that are already on the false positives list.
            try:
                if results["query"]["pages"][id]["pageprops"]["wikibase_item"] in false_positives:
                    continue
            except KeyError:
                pass
            try:
                #print('Wikipedia article doesn\'t have a Wikidata link',
                #        results["query"]["pages"][id], qid)
                #print('Possible false positive: Wikipedia page',
                #    results["query"]["pages"][id]['title'],
                #    'created after dump creation.')
                print('Checking if the page was created before dump creation time.')
                key = self.compare_creation_dates(id, results)
                try:
                    false_positives.append(key)
                except KeyError:
                    pass
                continue
            except UnboundLocalError:
                pass

            print('Wikipedia article doesn\'t have a Wikidata link',
                    results["query"]["pages"][id], 'unknown QID')
            print('Possible false positive: Wikipedia page needs purging.')
            self.needs_purging.append(results["query"]["pages"][id]['title'])
            #self.purge_page(urlencode(results["query"]["pages"][id]['title']))
            #time.sleep(1)

        '''
        for title in false_positive_label:
            for qid in self.dump.keys():
                if self.dump[qid] == title:
                    false_positives.append(qid)
                    break
        '''

        return false_positives


    def query_revisions_from_wikipedia_api(self, title):
        # https://sv.wikipedia.org/w/api.php?action=query&prop=revisions&rvlimit=1&rvprop=timestamp&rvdir=newer&titles=titles&format=json
        #api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        print('Querying', self.api_url)
        data = {"action": "query", "prop": "revisions", "rvlimit": "1",
                "rvprop": "timestamp", "rvdir": "newer",
                "format": "json", "titles": title }
        raw = urlopen(self.api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res


    '''
    Pages in certain namespaces shouldn't be linked to Wikidata.
    Sometimes they still are. They are outside the scope of this script.

    Function recieves a list of
    '''
    def remove_links_to_out_of_scope_namespaces(self, results):
        # User namespace pages are not in wd dump. They need to be removed manually.
        '''
        '4962228': {'pageid': 4962228, 'ns': 10, 'title': 'Template:Black project',
        'pageprops': {'wikibase_item': 'Q6720862'}}, '3574296':
        {'pageid': 3574296, 'ns': 10, 'title': 'Template:Brookhaven, New York',
        'pageprops': {'wikibase_item': 'Q6730751'}
        '''
        unwanted_namespaces = [2, 3, 4, 5, 11]
        false_positives = []
        false_positives_label = []
        for id in list(results["query"]["pages"]):
            item = results["query"]["pages"][id]
            if item['ns'] in unwanted_namespaces:
                false_positives_label.append(results['query']['pages'][id]['title'])

        # Search qids that match the titles.
        for title in false_positives_label:
            for qid in self.dump.keys():
                if self.dump[qid] == title:
                    false_positives.append(qid)
                    break

        return false_positives


    # TODO: This should be made in object-oriented way.
    def search_false_positives(self):
        wd_results = []
        wp_results = []
        false_positives = []
        print(len(self.dump))

        qids = list(self.dump.keys())
        labels = list(self.dump.values())

        # Get 50 items from Wikidata and Wikipedia
        for i in range(0, len(qids), 50):
            wd_results = self.query_wikidata_api(qids[i:i+50])
            #print(wd_results)  # User-nimiavaruuden sivut ovat tässä
            time.sleep(1)
            false_positives += self.parse_qids(wd_results)

            wp_results = self.query_wikipedia_api(labels[i:i+50])
            false_positives += self.parse_labels(wp_results)
            false_positives += self.remove_links_to_out_of_scope_namespaces(wp_results)
            time.sleep(1)

        # Purge pages and redo false positive search on purged pages.
        #self.purge_page(urlencode(results["query"]["pages"][id]['title']))

        if self.needs_purging:
            print('Purge pages')
            self.purge_page(self.needs_purging)
            wp_results = self.query_wikipedia_api(self.needs_purging)
            print(self.needs_purging)
            print(wp_results)
            false_positives += self.parse_labels(wp_results)
            false_positives += self.remove_links_to_out_of_scope_namespaces(wp_results)


        return false_positives  # False positives


if __name__ == '__main__':
    with open('tmp_out.json', 'r') as infile:
        data = json.load(infile)

    print('Q6613346', data['Q6613346'])

    verifier = Verifier(data, "en")
    false_positives = verifier.run_verification_queries()
    print(false_positives)
    print(len(false_positives))
