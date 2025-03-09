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
import logging

'''
Index file article name process:
1. iterate_index_file
2. unescape_part
3. compare_to_sparql_results
4. parse_line
'''

def parse_qid(url):
    return url.split('/')[-1]

def unescape_part(out):
    try:
        txt = html.unescape(out.decode('utf-8'))
    except UnicodeDecodeError:
        '''
        txt = html.unescape(
            out[:out.rindex(b'\n')].decode('utf-8'))
        '''
        try:
            txt = html.unescape(
                out[:out.rindex(b'\n')].decode('utf-8'))
        except ValueError:
            #print(out)
            txt = b''.decode('utf-8')
    return txt #.encode('utf-8')


class DeadLinkFinder(object):
    def __init__(self, lang, wikiproject, dump_time, query_filepath):
        self.lang = lang
        self.wikiproject = wikiproject.replace('-', '_')
        self.sparql_query_filepath = query_filepath
        self.dump_time = dump_time
        self.page_dict = {}
        #self.namespace_name = self.get_template_namespace_name()
        self.sparql_query_result_file = self.wikiproject + '_query_results.json'
        (self.index_filepath, self.date) = self.get_index_filepath()
        self.query_wikidata_sparql_service()
        self.parse_json()
        self.original_sparql_result_len = len(self.page_dict)


    def run(self):
        start_time = time.time()

        print('Process started at', time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(start_time)))
        try:
            print(self.index_filepath)
            self.iterate_index_file()
            #print(process.page_dict)
            print(time.time() - start_time)
            # TODO: Remove pages in user namespace as they cannot be verified from the dump file.

            results = self.save_results()
            self.verify_results(results)
            print(time.time() - start_time)
        except KeyboardInterrupt:
            print(time.time() - start_time)


    # As of 13.11.2021 this function isn't called anywhere from this file.
    # Added comments to find out if it's called from some other file.
    # This is neccessary to find out why this script thinks templates
    # in user namespace are deleted.
    '''
    def get_template_namespace_name(self):
        api_url = 'https://' + self.lang + '.wikipedia.org/w/api.php'
        data = {"action": "query", "format": "json",
                "meta": "siteinfo", "siprop": "namespaces" }
        raw = urlopen(api_url, urlencode(data).encode()).read()
        res = json.loads(raw)
        return res['query']['namespaces']["10"]['*']
    '''


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
        index = requests.get(base_url).text  # TODO: Handle socket.gaierror: [Errno -3] Temporary failure in name resolution
        soup_index = BeautifulSoup(index, 'html.parser')
        dumps = [(a['href'], a.next_sibling) for a in soup_index.find_all('a') if
                 a.has_attr('href')]
        for (item, line) in dumps:
            if expected_filename_str in item and '-rss.xml' not in item:
                print( ( item, self.parse_date(line.strip()) ) )
                return (base_url + '/' + item, self.parse_date(line.strip()))
        return None


    def query_wikidata_sparql_service(self):
        with open(self.sparql_query_filepath) as queryfile:
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
                # 7.11.2020 After change in sparql.py, removed encoding='utf-8' here.
                data = json.load(infile) # , encoding='utf-8'
            #sys.exit()
            os.remove(self.sparql_query_result_file)
            #print(len(data))
        except FileNotFoundError:
            print('File:', self.sparql_query_result_file, 'not found. Nothing was done.')
            #sys.exit()
            return
        for item in data:
            sitelink = urllib.parse.unquote(item['sitelink']).replace('_', ' ')
            #sitelink = nescape_part(item)
            #print(sitelink.replace(base_url, ''))
            # 7.11.2020 After change in sparql.py, removed encoding='utf-8' here.
            self.page_dict[
                sitelink.replace(base_url, '') #.encode('utf-8')
                ] = parse_qid(item['item'])
            #print(type(sitelink.replace(base_url, '')))
            #sys.exit()


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
            for chunk in input_stream.iter_content(chunk_size=2048):  # 4096
                str_from_stream += decompressor.decompress(chunk)
                txt = unescape_part(str_from_stream)
                if '\n' not in txt:  # Contains end of line.
                    continue
                self.compare_to_sparql_results(txt)
                last_index = str_from_stream.rindex(b'\n')
                str_from_stream = str_from_stream[last_index+1:]



    def parse_line(self, line):
        '''
        Retreves a page-title from a string line that is
        formated as 'file-offset:page-id:page-title'.

        Returns the page_title.

        '''
        tmp = line.strip().split(':')
        page_title = ':'.join(tmp[2:])
        return page_title


    def compare_to_sparql_results(self, dump_txt):
        '''
        Compares an page name from an index file to page
        names from a sparql query. If a match is found, deletes the page
        name from dictionary.

        '''
        for i, line in enumerate(dump_txt.splitlines()):
            title = self.parse_line(line)
            if not title:
                continue
            try:
                del self.page_dict[title]
            except KeyError:
                continue
            if len(self.page_dict) % 5000 == 0:
                print(len(self.page_dict))


    def save_results(self):
        results = {}
        for label in self.page_dict.keys():
            try:
                results[self.page_dict[label]] = label.decode('utf-8')
            except AttributeError:
                results[self.page_dict[label]] = label
        with open('tmp_out.json', 'w') as outfile:
            json.dump(results, outfile)
        return results


    def verify_results(self, results):
        if not results:
            return
        print(str(len(results)) + '/' + str(self.original_sparql_result_len))
        if self.original_sparql_result_len == len(results):
            print('Comparing dump index with SPARQL results found no matches.')
            print('We shouldn\'t make large number of queries against live service.')
            print('Skipping this language')
            return  # Temp comment: remove # when done | I don't know why this was commented out.
        print('Verifying sitelinks.')
        verifier = Verifier(results, self.lang, self.date)
        false_positives = verifier.search_false_positives()
        lines = []
        tab = '	'
        for item in results:
            if item in false_positives:
                #print('Skipping', item, results[item])
                continue
            #line = '|'.join(['-' + item, 'S' + self.lang + 'wiki', '"' + results[item] + '"']) +\
            #       ' /* Page on [' + self.lang + 'wiki] deleted. */'
            line = '|'.join([item, 'S' + self.lang + 'wiki', '""']) +\
                   ' /* Page on [' + self.lang + 'wiki] deleted. */'
            lines.append(line)
            print(line)

        if lines:
            with open('./query_results/' + self.lang + '_deleted_sitelinks.txt', 'w') as outfile:
                outfile.write('\n'.join(lines))



def get_wd_lang_names(lang_code_filepath):
    try:
        with open(lang_code_filepath) as infile:
            data = json.load(infile)
    except FileNotFoundError:
        print('Error: File ' + lang_code_filepath + ' not found. Aborting.')
        sys.exit(1)
    return [data[i]['wmLangCode'] for i in range(len(data))]

# TODO: Don't verify that sitelinks are in the right namespace.
# Templates exist in user namespace too.


def main(included_languages=None, start_from=None, skipped_languages=None):
    if included_languages:
        wm_lang_codes = included_languages
        if skipped_languages:
            for l in wm_lang_codes:
                if l in skipped_languages:
                    logging.warning(
                        'You are skipping a language "' + l +
                        '" which you\'ve explicitly included.')
    else:
        wm_lang_codes = get_wd_lang_names('./delifi/wikimedia_lang_codes.json')
    found = False
    start_time = time.time()

    for i, lang in enumerate(wm_lang_codes, 1):
        if start_from:
            if lang == start_from:
                found = True
            if not found:
                continue

        if lang in skipped_languages:
            logging.info('Skipping languge', lang, 'from skilled languages list.')
            continue

        lang_count = '(%i/%i)' % (i, len(wm_lang_codes))
        print('Processing language:', lang, lang_count)
        try:
            # './delifi/queries/query_single_sitelink.sprql'
            process = DeadLinkFinder(
                lang, lang + 'wiki', 'latest',
                './delifi/queries/query_single_sitelink_disambig.sprql')
        except TypeError as e:
            print(e)  # e.g. ru-sib, tlh
            continue
        process.run()
        time.sleep(2)
    print(time.time() - start_time)

# TODO: Limit namespaces. This script would fullfil its job better if it
# didn't have to deal with e.g. talk pages.
# TODO: Add logging. It's needed to make troubleshooting more tolerable.

if __name__ == '__main__':
    skipped_languages = [] # ['vec'] # , 'en', 'da']  # 'da',
    start_from = '' # 'lfn'  # None # 'gan' #'hi' # 'be-tarask' # 'ru-sib' # 'de' # lang code
    #included_languages = [{'wmLangCode': 'vec' }]
    included_languages = [] #
    if skipped_languages:
        logging.info('Skipping languages:', ', '.join(skipped_languages))
    if start_from:
        logging.info('Start from language:', start_from)
    if included_languages:
        logging.info('Including only languages:', ', '.join(included_languages))
    main(included_languages, start_from, skipped_languages)
