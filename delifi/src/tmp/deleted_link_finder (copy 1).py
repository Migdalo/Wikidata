from bs4 import BeautifulSoup
from sitelink_verifier import Verifier
import requests
import bz2
import json
import sys
import time
import urllib.parse
import binascii
import html
import argparse


def parse_qid(url):
    return url.split('/')[-1]

def print_potential_filenames(dumps):
    for line in dumps:
        if line.startswith(filename_start) and\
            line.endswith(filename_ends):
            print(line)

class Item(object):

    def __init__(self, sq, sl):
        self.sparql_qid = sq
        self.sparql_link = sl
        self.dump_qid = None
        self.dump_link = None
        self.wd_query_qid = None
        self.wd_query_link = None
        self.wp_query_qid = None
        self.wp_query_link = None
        self.is_complete = False

    def set_completed(self):
        self.is_complete = True

    def set_done(self):
        self.set_complete()

    def is_complete(self):
        return self.is_complete

    def is_done(self):
        return self.is_complete()

    def add_dump_data(self, qid, link):
        self.dump_qid = qid
        self.dump_link = link

    def add_wd_data(self, qid, link):
        self.wd_query_qid = qid
        self.wd_query_link = link

    def add_wp_data(self, qid, link):
        self.wp_query_qid = qid
        self.wp_query_link = link

    def get_all_qids(self)
        return [
            self.sparql_qid,
            self.dump_qid,
            self.wd_query_qid,
            self.wp_query_qid
            ]

    def get_all_links(self)
        return [
            self.sparql_link,
            self.dump_link,
            self.wd_query_link,
            self.wp_query_link
            ]

    def has_all_links(self):
        return all(self.get_all_links())

    def has_all_qids(self):
        return all(self.get_all_qids())

    def assert_qid_is_validated(self):
        return self.sparql_qid == self.dump_qid == self.wd_query_qid == self.wp_query_qid

    def assert_link_is_validated(self):
        return self.sparql_link == self.dump_link == self.wd_query_link == self.wp_query_link

    def assert_dump_and_sparql_have_same_values(self):
        return (self.sparql_qid == self.dump_qid) and (self.sparql_link == self.dump_link)

    def assert_dump_equals_wp(self):
        '''
        Detects possible false positives:
        - dump:wrong wp:right == Item was moved between dump creation and running this script
        - dump:right wd:wrong == ??? redirects ???
        - both wrong          == ???
        - both right          == all is good
        '''
        return (self.wp_query_qid == self.dump_qid) and (self.wp_query_link == self.dump_link)

    def assert_sparql_equals_wd(self):
        '''
        Detects possible false positives:
        - sparql:wrong wd:right == SPARQL service sometimes returns old values
        - sparql:right wd:wrong == ??? redirects ???
        - both wrong            == ???
        - both right            == all is good
        '''
        return (self.wd_query_qid == self.sparql_qid) and (self.wd_query_link == self.sparql_link)

    def assert_wd_equals_wp(self):
        '''
        Detects possible false positives:
        - wp:wrong wd:right  == ???
        - wp:right wd:wrong  == true duplicates caused by a software bug
        - both wrong         == ??? wtf ???
        - both right         == all is good
        '''
        return self.assert_wd_qid_equals_wp_qid() and \
               self.assert_wd_link_equals_wp_link()

    def assert_wd_qid_equals_wp_qid(self):
        return (self.wd_query_qid == self.wp_query_qid)

    def assert_wd_link_equals_wp_link(self):
        return (self.wd_query_link == self.wp_query_link)

class Parser(object):

    def __init__(self, lang, dump_time, input_json_file='query.json'):
        self.lang = lang
        self.wikiproject = lang + 'wiki'
        self.dump_time = dump_time
        self.input_filename = input_json_file
        self.base_url = 'https://dumps.wikimedia.org/' +\
            self.wikiproject + '/' + self.dump_time
        self.template_dict = self.parse_json()

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
                    sitelink.replace(base_url, '').encode('utf-8')
                    ] = parse_qid(item['item'])
        return template_list


    def unescape_part(self, out, last_index):
        try:
            txt = html.unescape(out[last_index:].decode('utf-8'))
        except UnicodeDecodeError:
            txt = html.unescape(
                out[last_index:out.rindex(b'\n')].decode('utf-8'))
        return txt.encode('utf-8')

    def parse_and_delete_found(self, txt):
        for line in txt.splitlines():
            tmp = line.strip().split(b':')
            label = b':'.join(tmp[2:])
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
                txt = self.unescape_part(out, last_index)
                if b'\n' not in txt:
                    continue
                self.parse_and_delete_found(txt)
                last_index = out.rindex(b'\n')


    def process_dump_index_files(self):
        index = requests.get(self.base_url).text
        soup_index = BeautifulSoup(index, 'html.parser')
        dumps = [a['href'] for a in soup_index.find_all('a') if
                 a.has_attr('href')]

        # /enwiki/20200120/enwiki-20200120-pages-articles-multistream-index27.txt-p57663464p59163464.bz2
        filename_start = self.wikiproject + '-' + self.dump_time +\
            '-pages-articles-multistream-index'  # latest
        #filename_start = '/' + self.wikiproject + '/' + self.dump_time + '/' + filename_start
        filename_start = '/' + '/'.join(
            [self.wikiproject, self.dump_time, filename_start])
        filetype = '.txt'
        filename_ends = '.bz2'
        filenumber = 1

        print(self.base_url)
        print(filename_start)

        file_log = []
        while True:
            filename = None
            found_line = False
            for line in dumps:
                if not (line.startswith(filename_start) and
                        line.endswith(filename_ends)):
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

            #print(filename)
            self.find_missing_templates(
                filename.replace('/' + self.wikiproject + '/' + self.dump_time + '/', ''))
            time.sleep(2)




def main(get_new_data = True):
    start_time = time.time()
    dump_time = '20200201'
    parser = Parser('en', dump_time)

    if get_new_data == True:
        parser.process_dump_index_files()

        results = {}
        for label in parser.template_dict.keys():
            results[parser.template_dict[label]] = label.decode('utf-8')

        print(results)
        print(len(results))
        print(len(parser.template_dict))
        print(time.time() - start_time)

        with open('tmp_out.json', 'w') as outfile:
            json.dump(results, outfile)

    else:
        with open('tmp_out.json', 'r') as infile:
            results = json.load(infile)

    verifier = Verifier(results, "en")
    false_positives = verifier.run_verification_queries()

    tab = '	'
    for item in results:
        if item in false_positives:
            print('Skipping', item, results[item])
            continue
        line = '|'.join(['-' + item, 'S' + parser.lang + 'wiki', '"' + results[item] + '"']) +\
               ' /* Page on [' + parser.lang + 'wiki] deleted. */'
        print(line)
    print(time.time() - start_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', '-r', action='store_true',
        default=False, help='Redownload data.')
    args = parser.parse_args()
    main(args.refresh)
