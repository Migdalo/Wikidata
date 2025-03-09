from bs4 import BeautifulSoup
from sitelink_verifier import Verifier
from datetime import datetime
import requests
import bz2
import sparql
import json
import sys
import urllib.parse
import html
import time
import os


def parse_qid(url):
    return url.split('/')[-1]

def unescape_part(out, last_index):
    try:
        txt = html.unescape(out[last_index:].decode('utf-8'))
    except UnicodeDecodeError:
        txt = html.unescape(
            out[last_index:out.rindex(b'\n')].decode('utf-8'))
    return txt.encode('utf-8')


class DeadLinkFinder(object):
    def __init__(self, lang, wikiproject, dump_time):
        self.lang = lang
        self.wikiproject = wikiproject
        self.dump_time = dump_time
        self.page_dict = {}
        #self.namespace_name = self.get_template_namespace_name()
        self.sparql_query_result_file = self.wikiproject + '_query_results.json'
        (self.index_filepath, self.date) = self.get_index_filepath()
        self.query_wikidata_sparql_service()
        self.parse_json()


    def get_template_namespace_name(self):
        api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        data = {"action": "query", "format": "json",
                "meta": "siteinfo", "siprop": "namespaces" }
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res['query']['namespaces']["10"]['*']


    def parse_date(self, str):
        '''
        Gets a string as a parameter. The string contains,
        but is not limited to, a date in format: 03-Oct-2020 01:01.

        Returns a datetime object.

        '''
        date_str = str.split('    ')[0]
        return datetime.strptime(date_str, "%d-%b-%Y %H:%M")


    def get_index_filepath(self):
        '''
        Queries Wikimedia dumps site (https://dumps.wikimedia.org/) for
        a language spesific index file.

        Returns an url to the langauge spesific index file
        or None if an index file wasn't found.

        '''
        expected_filename_str = 'pages-articles-multistream-index.txt.bz2'
        base_url = 'https://dumps.wikimedia.org/' +\
            self.wikiproject + '/' + self.dump_time
        index = requests.get(base_url).text
        soup_index = BeautifulSoup(index, 'html.parser')
        dumps = [(a['href'], a.next_sibling) for a in soup_index.find_all('a') if
                 a.has_attr('href')]
        for (item, line) in dumps:
            if expected_filename_str in item and '-rss.xml' not in item:
                print( ( item, self.parse_date(line.strip()) ) )
                return (base_url + '/' + item, self.parse_date(line.strip()))
        return None


    def query_wikidata_sparql_service(self):
        with open('./delifi/queries/query_single_sitelink.sprql') as queryfile:
            query = queryfile.read().strip().replace('LANG', self.lang)
        #print(query)
        sparql.query_wikidata(query, self.sparql_query_result_file)


    def parse_json(self):
        '''
        Adds items from sparql result file to a dictionary.

        '''
        # https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2
        base_url = 'https://' + self.lang + '.wikipedia.org/wiki/'
        try:
            with open(self.sparql_query_result_file, 'r') as infile:
                data = json.load(infile, encoding='utf-8')
            os.remove(self.sparql_query_result_file)
        except FileNotFoundError:
            print('File:', self.sparql_query_result_file, 'not found. Nothing was done.')
            sys.exit()
        for item in data:
            sitelink = urllib.parse.unquote(item['sitelink']).replace('_', ' ')
            self.page_dict[
                sitelink.replace(base_url, '').encode('utf-8')
                ] = parse_qid(item['item'])


    def iterate_index_file(self):
        '''
        Downloads an index file from Wikimedia dumps site.

        '''
        #filename = self.index_filepath
        decompressor = bz2.BZ2Decompressor()
        str_from_stream = b''
        last_index = 0
        with requests.get(self.index_filepath, stream=True) as input_stream:
            input_stream.raise_for_status()
            for chunk in input_stream.iter_content(chunk_size=2048):
                str_from_stream = str_from_stream + decompressor.decompress(chunk)
                txt = unescape_part(str_from_stream, last_index)
                if b'\n' not in txt:  # Find end of line.
                    continue
                self.compare_to_sparql_results(txt)
                last_index = str_from_stream.rindex(b'\n')



    def parse_line(self, line):
        '''
        Retreves a page-title from a string line that is
        formated as 'file-offset:page-id:page-title'.

        Returns the page_title.

        '''
        tmp = line.strip().split(b':')
        page_title = b':'.join(tmp[2:])  #
        return page_title


    def compare_to_sparql_results(self, txt):
        '''
        Compares an page name from an index file to page
        names from a sparql query. If a match is found, deletes the page
        name from dictionary.

        '''
        for i, line in enumerate(txt.splitlines()):
            title = self.parse_line(line)
            if not title:
                continue

            #if len(self.page_dict) <= 5000 and len(self.page_dict) % 100 == 0:
            #    time.sleep(1)
            #if len(self.page_dict) <= 5000 and i % 500 == 0:
            #    time.sleep(1)
            try:
                del self.page_dict[title]
            except KeyError:
                '''
                if len(self.page_dict) < 3000 and len(self.page_dict) % 10 == 0:
                    time.sleep(1)
                elif len(self.page_dict) < 5000 and len(self.page_dict) % 100 == 0:
                    time.sleep(1)
                '''
                continue
            if len(self.page_dict) % 1000 == 0:
                print(len(self.page_dict))
                time.sleep(0.5)


    def save_results(self):
        results = {}
        for label in self.page_dict.keys():
            results[self.page_dict[label]] = label.decode('utf-8')
        with open('tmp_out.json', 'w') as outfile:
            json.dump(results, outfile)
        return results


    def verify_results(self, results):
        if not results:
            return
        print('Verifying sitelinks.')
        verifier = Verifier(results, self.lang, self.date)
        false_positives = verifier.search_false_positives()

        lines = []

        tab = '	'
        for item in results:
            if item in false_positives:
                #print('Skipping', item, results[item])
                continue
            line = '|'.join(['-' + item, 'S' + self.lang + 'wiki', '"' + results[item] + '"']) +\
                   ' /* Page on [' + self.lang + 'wiki] deleted. */'
            lines.append(line)
            print(line)

        if lines:
            with open('./query_results/' + self.lang + '_deleted_sitelinks.txt', 'w') as outfile:
                outfile.write('\n'.join(lines))


def main(lang, dump_time):
    start_time = time.time()

    print('Process started at', time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(start_time)))
    try:
        try:
            process = DeadLinkFinder(lang, lang + 'wiki', dump_time)
        except TypeError:
            print('TypeError. Aborting.')
            return
        print(process.index_filepath)
        process.iterate_index_file()
        #print(process.page_dict)
        print(time.time() - start_time)
        results = process.save_results()
        process.verify_results(results)
        print(time.time() - start_time)
    except KeyboardInterrupt:
        print(time.time() - start_time)



if __name__ == '__main__':
    lang_code_file = './delifi/wikimedia_lang_codes.json'
    start_from = 'en'
    found = False
    try:
        with open(lang_code_file) as infile:
            wm_lang_codes = json.load(infile)
    except FileNotFoundError:
        print('Error: File ' + lang_code_file + ' not found. Aborting.')
        sys.exit(1)
    for lang in wm_lang_codes:
        #print(lang['wmLangCode'])
        if lang['wmLangCode'] == start_from:
            found = True
        if not found:
            continue
        print('Processing language:', lang['wmLangCode'])
        main(lang['wmLangCode'], 'latest')
        break  # Let's stop here for testing. Remove after testing is done.
        time.sleep(2)
    '''
    for lang in ['en', 'fi', 'test']:
        main(lang, 'latest')

    main('en', 'latest')
    '''
