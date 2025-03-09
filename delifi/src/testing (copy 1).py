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


class DumpFileIterator(object):
    def __init__(self, lang, wikiproject, dump_time):
        self.lang = lang
        self.wikiproject = wikiproject.replace('-', '_')
        self.dump_time = dump_time
        self.page_dict = {}
        #self.namespace_name = self.get_template_namespace_name()
        self.sparql_query_result_file = self.wikiproject + '_query_results.json'
        (self.index_filepath, self.date) = self.get_index_filepath()
        self.query_wikidata_sparql_service()
        self.parse_json()
        self.original_sparql_result_len = len(self.page_dict)


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
                # 7.11.2020 After change in sparql.py, removed encoding='utf-8' here.
                data = json.load(infile) # , encoding='utf-8'
            #sys.exit()
            os.remove(self.sparql_query_result_file)
            #print(len(data))
        except FileNotFoundError:
            print('File:', self.sparql_query_result_file, 'not found. Nothing was done.')
            sys.exit()
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
                '''
                try:
                    txt = txt.decode('utf-8')
                except AttributeError:
                    txt = txt
                '''
                self.compare_to_sparql_results(txt)
                last_index = str_from_stream.rindex(b'\n')
                str_from_stream = str_from_stream[last_index+1:]



    def parse_line(self, line):
        '''
        Retreves a page-title from a string line that is
        formated as 'file-offset:page-id:page-title'.

        Returns the page_title.

        '''
        #tmp = line.strip().split(b':')
        #page_title = b':'.join(tmp[2:])  #
        tmp = line.strip().split(':')
        page_title = ':'.join(tmp[2:])  #
        return page_title


    def compare_to_sparql_results(self, dump_txt):
        '''
        Compares an page name from an index file to page
        names from a sparql query. If a match is found, deletes the page
        name from dictionary.
        b'Mod\xc3\xa8l:+1'

        '''

        for i, line in enumerate(dump_txt.splitlines()):
            title = self.parse_line(line)
            if not title:
                continue

            '''
            for key in self.page_dict.keys():
                if title.startswith('Mod'):
                    print(title, '==', key)
                if title == key:
                    sys.exit()
            '''
            try:
                del self.page_dict[title]
            except KeyError:
                continue
            if len(self.page_dict) % 1000 == 0:
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
            #return  # Temp comment: remove # when done
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


class DeadLinkFinder(object):

    def __init__(self, lang):
        self.lang = lang
        pass

    def main(self):
        start_time = time.time()

        print('Process started at', time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(start_time)))
        try:
            try:
                process = DumpFileIterator(self.lang, self.lang + 'wiki', 'latest')
            except TypeError as e:
                print(e)  # e.g. ru-sib, tlh
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



def get_wd_lang_names(lang_code_filepath):
    try:
        with open(lang_code_filepath) as infile:
            return json.load(infile)
    except FileNotFoundError:
        print('Error: File ' + lang_code_filepath + ' not found. Aborting.')
        sys.exit(1)
    return None

# TODO: Verify that sitelinks are in the right namespace.

def run():
    included_languages = [{'wmLangCode': 'vec' }]
    try:
        wm_lang_codes = included_languages
    except NameError:
        wm_lang_codes = get_wd_lang_names('./delifi/wikimedia_lang_codes.json')
    skipped_languages = ['da']  # , 'vec'
    start_from = None #'ru-sib' # 'de' # lang code
    found = False
    start_time = time.time()
    #print(wm_lang_codes)
    #sys.exit()
    for i, lang in enumerate(wm_lang_codes, 1):
        #print(lang)
        if start_from:
            if lang['wmLangCode'] == start_from:
                found = True
            if not found:
                continue

        if lang['wmLangCode'] in skipped_languages:
            continue

        lang_count = '(%i/%i)' % (i, len(wm_lang_codes))
        print('Processing language:', lang['wmLangCode'], lang_count)
        process = DeadLinkFinder(lang['wmLangCode'])
        process.main()
        #if start_from:
        #    break  # Let's stop here for testing. Remove after testing is done.
        time.sleep(1)
    print(time.time() - start_time)


if __name__ == '__main__':
    run()
