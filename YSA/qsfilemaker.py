# -*- coding: UTF-8
from simplelinkedlist import LinkedList, Node
import json
import argparse
import sys


class WDID(object):

    @staticmethod
    def validate_id(idn, char):
        '''
        Gets the first character of the id type and an id as a parameter.
        Checks that the id starts with the character and that all other
        characters are digits. Returns True if boths checks are successful,
        otherwise returns False.
        '''
        if not idn.upper().startswith(char):
            return False
        else:
            return idn[1:].isdigit()

    @staticmethod
    def get_validated_qid(qnumber):
        '''
        Recieves a Wikidata qid, or a Wikidata url that ends with a qid,
        as a parameter, resolves the qid from the parameter and validates it.
        If validation is successful, returns the validated qid.
        Otherwise, raises a ValueError.
        '''
        try:
            if WDID.validate_qid(qnumber):
                return qnumber.upper()
            else:
                raise ValueError
        except ValueError:
            qnumber = WDID.get_qid(qnumber)
            if WDID.validate_qid(qnumber):
                return qnumber.upper()
            else:
                raise ValueError('Invalid QID:', qnumber)

    @staticmethod
    def validate_pid(pid):
        '''
        Gets a property id as a parameter, and verifies it.
        Returns True if successfull, otherwise return False.
        '''
        return WDID.validate_id(pid, 'P')

    @staticmethod
    def validate_qid(qid):
        '''
        Gets a item id as a parameter, and verifies it.
        Returns True if successfull, otherwise return False.
        '''
        return WDID.validate_id(qid, 'Q')

    @staticmethod
    def get_qid(url):
        '''
        Gets a Wikidata item url as a parameters, parses
        an item id from the end of the url and returns it.
        '''
        return url.split('/')[-1]

    @staticmethod
    def get_qnumber(url):
        return WDID.get_qid(url)

    @staticmethod
    def qid_to_url(qid):
        return 'https://www.wikidata.org/wiki/' + qid

class WDDate(object):
    separators = '.:/'

    def __init__(self, date=None, year=None, month=None, day=None, scale=None):
        if not date:
            if not any(year, month, day):
                raise ValueError('Missing parameter. Throw me a bone here...')
            self.year = None
            self.month = None
            self.day = None
            self.scale = None
        else:
            self.parse_date(date)

    def parse_date(self, date):
        s = set([x for x in date if x in separators])
        if len(s) != 1:
            raise ValueError(
                'Failed to parse date. Too many punctuation marks.',
                'Throw me less bones here, please.')
        p = date.split(list(s)[0])


class QSLine(object):

    TAB = '	'

    def __init__(self, qnumber, removal=False, create=False):
        if create:
            self.qnumber = 'LAST'
        else:
            self.qnumber = WDID.get_validated_qid(qnumber)
        if removal:
            self.line = '-' + self.qnumber
        else:
            self.line = self.qnumber

    def add_to_line(self, pnumber, value):
        if not WDID.validate_pid(pnumber):
            raise ValueError('Invalid PID:', pnumber)
        self.line += QSLine.TAB + pnumber + QSLine.TAB + value

    def conditional_add(self, pnumber, value):
        if value:  # E.g. follows/followed by
            self.add_to_line(pnumber, value)

    def add_qid_to_line(self, pnumber, value):
        value = WDID.get_validated_qid(value)
        self.add_to_line(pnumber, value)

    def add_qid(self, pnumber, qnumber):
        self.add_qid_to_line(pnumber, qnumber)

    def add_qualifier(self, pnumber, value):
        self.add_to_line(pnumber, value)

    def add_string_to_line(self, pnumber, value):
        '''
        In QS many values have to be wrapped inside quotations marks.
        This function will automatically add quotation marks to the
        property value and then add it to the QS line.
        '''
        #self.add_to_line(pnumber, value)
        if value[0] in '\'"' and value[-1] in '\'"':
            self.add_to_line(pnumber, value)
        else:
            self.add_to_line(pnumber, '"' + value + '"')

    def add_lang_specific_string(self, pnumber, value, lang):
        self.add_to_line(pnumber, '"' + lang + ':' + value + '"')

    def add_comment(self, comment):
        self.line += ' */' + comment + '*/'

    def add_label(self, language, label):
        pass

    def add_sources(self):
        porvoo_url = 'http://www.porvoo.fi/index.php?mid=1370'
        porvoo_archive_url = \
            'https://web.archive.org/web/20160308223323/http://www.porvoo.fi/index.php?mid=1370'
        kirjasampo_url = \
            'http://www.kirjasampo.fi/fi/kulsa/saha3%253Au8801e79a-ad42-476f-8164-c0488e5bd3d8'
        p_archive_url = 'S1065'
        p_ref_url = 'S854'
        '''
        self.line += QSLine.TAB + p_ref_url + QSLine.TAB + '"' + porvoo_url + '"' +\
                     QSLine.TAB + p_archive_url + QSLine.TAB + '"' + porvoo_archive_url + '"' +\
                     QSLine.TAB + 'S1476' + QSLine.TAB + 'fi:"Runeberg-palkinto"' +\
                     QSLine.TAB + 'S2960' + QSLine.TAB + '+2016-03-08T00:00:00Z/11'
                     #QSLine.TAB + 'S813' + QSLine.TAB + '+2017-12-14T00:00:00Z/11'
        '''
        self.line += QSLine.TAB + p_ref_url + QSLine.TAB + '"' + kirjasampo_url + '"' +\
                     QSLine.TAB + 'S1476' + QSLine.TAB + 'fi:"Runeberg-palkinto"' +\
                     QSLine.TAB + 'S813' + QSLine.TAB + '+2017-12-14T00:00:00Z/11'

    def get_line(self):
        if self.line.endswith('\n'):
            return self.line
        else:
            return self.line + '\n'


def QSCreate(QSLine):

    def __init__(self):
        self.line = ['CREATE']
        self.languages = []
        self.statements = []

    def add_statement(self, pnumber, value):
        #line = QSLine('LAST', create=True)
        if not WDID.validate_pid(pnumber):
            raise ValueError('Invalid PID:', pnumber)
        new_line = 'LAST' + QSLine.TAB + pnumber + QSLine.TAB + value
        self.line.append(new_line)

    def add_qualifier(self, pnumber, qnumber):
        pass

    def get_line(self):
        return '\n'.join(self.line)


class QSLangLine(QSLine):

    def __init__(self, qnumber, lang, removal=False):
        self.lang = lang
        self.removal = removal
        self.line = WDID.get_validated_qid(qnumber)

    def add_to_line(self, value_type, text):
        self.line += QSLine.TAB + value_type + self.lang + QSLine.TAB + '"' + text + '"'

    def add_label(self, label):
        self.add_to_line('L', label)

    def add_description(self, desc):
        self.add_to_line('D', desc)

    def add_alias(self, alias):
        self.add_to_line('A', alias)


class QSTimeLine(QSLine):
    def __init__(self, ll, suffix=None):
        self.suffix = suffix # True, False, None
        self.base_label = self.get_base_label(ll)

    def ll_to_labels(self):
        node = ll.head
        while True:
            try:
                if self.suffix:
                    text = self.base_label + ' ' + node.point_in_time
                elif self.suffix is False:
                    text = node.point_in_time + ' ' + self.base_label
                else:
                    text = self.base_label
            except AttributeError:
                break
            node = node.next


class QSFile(object):

    def __init__(self, filename='outfile'):
        self.data = []
        self.ll = LinkedList()
        self.filename = filename

    def print_data(self):
        self.ll.print_list()

    def print_qs_data(self):
        for line in self.data:
            print(line.get_line(), end='')

    def add_data_to_list(self, data):
        for item in data:
            qnumber = WDID.get_qnumber(item['item'])
            n = Node(qnumber, item['itemLabel'], item['year'])
            self.ll.add_node(n)

    def read_from_json(self, filename):
        with open(filename, 'r') as infile:
            data = json.load(infile)

        # Json to linked list
        for item in data:
            node = Node()

    def to_url(self):
        ''' Output the results as a QuickStatements 2 url. '''
        url = 'https://tools.wmflabs.org/quickstatements/#v1='
        node = self.ll.head
        count = 0
        tab = '%09'
        quote = '%22'
        newline = '%0A'
        while node:
            new_label = self.get_new_label(node)
            url += node.qnumber + tab + self.output_type[0] + self.lang
            url += tab + quote + new_label + quote + newline
            node = node.next
            count += 1
        url = url.replace(' ', '%20')
        print(count, 'items processed.')
        print('NOTICE: When opening the url in a browser, ' +
              'it might take a moment for the page to load.')
        if url[-3:] == newline:
            url = url[:-3].encode('utf-8')
        else:
            url = url.encode('utf-8')
        print(url, file=self.output_stream)

    def list_to_qs(self):
        pass

    def list_to_qs1(self):
        node = self.ll.head
        previous = None
        counter = 1
        while True:
            try:
                line = QSLine(node.qnumber)
            except AttributeError:
                break
            line.add_qualifier('P166', 'Q1183339')  # Award recieved
            line.add_to_line('P585', '+' + str(node.point_in_time) + '-00-00T00:00:00Z/09')
            if previous:  # Follows
                line.add_qualifier('P155', previous.qnumber)
            if node.next:  # Followed by
                line.add_qualifier('P156', node.next.qnumber)
            #line.add_string_to_line('P1545', str(counter))  # Series ordinal
            line.add_sources()
            self.data.append(line)
            previous = node
            node = node.next
            counter += 1
        self.print_qs_data()

    def save_to_file(self):
        with open(self.filename, 'w') as outfile:
            for line in self.data:
                outfile.write(line.get_line())
