from bs4 import BeautifulSoup
from sitelink_verifier import Verifier
import requests
import bz2
import json
import sys
import time
import urllib.parse
import html
import argparse
import re
import sparql


def parse_qid(url):
    return url.split('/')[-1]

def unescape_part(out, last_index):
    try:
        txt = html.unescape(out[last_index:].decode('utf-8'))
    except UnicodeDecodeError:
        txt = html.unescape(
            out[last_index:out.rindex(b'\n')].decode('utf-8'))
    return txt.encode('utf-8')


class Parser(object):

    def __init__(self, lang, dump_time='latest', input_json_file='query.json', querySparql):
        self.lang = lang
        self.wikiproject = lang + 'wiki'
        self.dump_time = dump_time
        self.input_filename = input_json_file
        self.base_url = 'https://dumps.wikimedia.org/' +\
            self.wikiproject + '/' + self.dump_time
        #self.template_dict = self.parse_json()
        self.template_dict = {}
        self.querySparql = querySparql
        if querySparql:
            self.query_wikidata_sparql_service()
        self.parse_json()

    def is_latest(self):
        return self.dump_time == 'latest'

    def query_wikidata_sparql_service(self):
        with open('Queryfile') as queryfile:
            query = queryfile.read().strip().rplace('LANG', self.lang)
        sparql.query_wikidata(query, self.input_filename)

    def parse_json(self):
        '''
        Add items from sparql result file to a dict.
        '''
        base_url = 'https://' + self.lang + '.wikipedia.org/wiki/'
        try:
            with open(self.input_filename, 'r') as infile:
                data = json.load(infile, encoding='utf-8')
        except FileNotFoundError:
            print('File:', self.input_filename, 'not found. Nothing was done.')
            sys.exit()
        for item in data:
            sitelink = urllib.parse.unquote(item['sitelink']).replace('_', ' ')
            self.template_dict[
                sitelink.replace(base_url, '').encode('utf-8')
                ] = parse_qid(item['item'])


    def parse_and_delete_found(self, txt):
        for line in txt.splitlines():
            tmp = line.strip().split(b':')
            label = b':'.join(tmp[2:])  # file-offset:page-id:page-title
            if not label:
                continue
            # Compare filename to sparql query
            try:
                del self.template_dict[label]
                if len(self.template_dict) % 1000 == 0:
                    print(len(self.template_dict))
            except KeyError:
                pass


    def find_missing_templates(self, filename):
        # Download a single file
        decompressor = bz2.BZ2Decompressor()
        fileurl = self.base_url + '/' + filename
        out = b''
        last_index = 0
        with requests.get(fileurl, stream=True) as input_stream:
            input_stream.raise_for_status()
            for chunk in input_stream.iter_content(chunk_size=2048):
                out = out + decompressor.decompress(chunk)
                txt = unescape_part(out, last_index)
                if b'\n' not in txt:
                    continue
                self.parse_and_delete_found(txt)
                last_index = out.rindex(b'\n')


    def get_multistream_url(self, filenamelist):
        # /fiwiki/20200801/fiwiki-20200801-pages-articles-multistream-index.txt.bz2
        # /enwiki/20200120/enwiki-20200120-pages-articles-multistream-index27.txt-p57663464p59163464.bz2
        filename = '-'.join([self.wikiproject, self.timestamp, 'pages-articles-multistream-index1'])
        #if self.lang in ['en', 'it', 'de', 'fr', 'pl', 'pt', 'ru']:
        #    filenumber = 1
        for filename in filenamelist:
            pass




    def process_dump_index_files(self):
        index = requests.get(self.base_url).text
        soup_index = BeautifulSoup(index, 'html.parser')
        dumps = [a['href'] for a in soup_index.find_all('a') if
                 a.has_attr('href')]
        #print(dumps)


        filename_start = self.wikiproject + '-' + self.dump_time +\
            '-pages-articles-multistream-index'  # latest
        #filename_start = '/' + self.wikiproject + '/' + self.dump_time + '/' + filename_start
        if not self.is_latest():
            filename_start = '/' + '/'.join(
                [self.wikiproject, self.dump_time, filename_start])
        filetype = '.txt'
        filename_ends = '.bz2'
        filenumber = 1

        print(self.base_url)
        print(filename_start)

        if not self.lang in ['en', 'it', 'de', 'fr', 'pl', 'pt', 'ru']:
            filename = filename_start + filetype + filename_ends
            if filename not in dumps:
                print('File' + filename + 'not found.')
                sys.exit()
            self.find_missing_templates(
                filename.replace('/' + self.wikiproject + '/' + self.dump_time + '/', ''))
            time.sleep(2)
            return

        file_log = []
        while True:
            filename = None
            found_line = False
            for line in dumps:
                #if not line.startswith(filename_start):
                #    continue
                if not line.endswith(filename_ends):
                    continue
                if not line.startswith(filename_start + str(filenumber) + filetype):
                    continue

                found_line = True
                if line not in file_log:
                    file_log.append(line)
                    filename = line
                    break

            if not found_line:
                print("Processed all the files.")
                break

            if not filename:
                filenumber += 1
                continue

            self.find_missing_templates(
                filename.replace('/' + self.wikiproject + '/' + self.dump_time + '/', ''))
            time.sleep(2)

'''
https://dumps.wikimedia.org/enwiki/20200201/enwiki-20200201-pages-articles-multistream-index2.txt-p30304p88444.bz2
https://dumps.wikimedia.org/enwiki/latest    /enwiki-latest-pages-articles-multistream-index2.txt-p30304p88444.bz2
'''

def main(lang, dump_time, offline=False, filepath='query.json' querySparql=False):
    start_time = time.time()
    parser = Parser(lang, dump_time, filepath, querySparql)

    if not offline:
        print('Retrieving dump file list.')
        parser.process_dump_index_files()

        results = {}
        for label in parser.template_dict.keys():
            results[parser.template_dict[label]] = label.decode('utf-8')

        #print(results)
        print(len(results))
        print(len(parser.template_dict))
        print(time.time() - start_time)

        with open('tmp_out.json', 'w') as outfile:
            json.dump(results, outfile)

    else:
        with open('tmp_out.json', 'r') as infile:
            results = json.load(infile)

    print('Verifying sitelinks.')
    verifier = Verifier(results, parser.lang)
    false_positives = verifier.search_false_positives()

    tab = '	'
    for item in results:
        if item in false_positives:
            #print('Skipping', item, results[item])
            continue
        line = '|'.join(['-' + item, 'S' + parser.lang + 'wiki', '"' + results[item] + '"']) +\
               ' /* Page on [' + parser.lang + 'wiki] deleted. */'
        print(line)
    print(time.time() - start_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='Wikimedia language code. ' +
        'Use "ALL" to iterate trought all languages.')
    parser.add_argument('--date', '-d', default='latest',
        help='Dump date in format [yyyymmdd]. Default: latest.')
    parser.add_argument('--file', '-f', default='query.json',
        help='Filepath to a json file from Wikidata\'s SPARQL query service.')
    parser.add_argument('--sparql', '-s', action='store_true', default=False,
        help='Program retrieves sparql results for you.')
    parser.add_argument('--offline', '-o', action='store_true',
        default=False, help='Don\'t re-download data.')
    args = parser.parse_args()
    rule = '^[1-2][0-9]{3}[0-1][0-9][0-3][0-9]$'
    m = re.search(rule, args.date)
    try:
        m.group(0)
    except AttributeError:
        if args.date != 'latest':
            raise parser.error('Incorrect date format.')
    if args.lang == 'ALL':
        try:
            with open('./delifi/queries/query_wikipedia_language_editions.sprql', 'r') as infile:
                query = infile.read().strip()
        except FileNotFoundError:
            raise parser.error('Sparql query file not found.')
        language_editions = sparql.query_wikidata(query, './delifi/wikipedia_language_editions.json')
        for le in language_edition:
            main(le['langCode'], args.date, args.offline, args.file, args.sparql)
    else:
        main(args.lang, args.date, args.offline, args.file, args.sparql)
