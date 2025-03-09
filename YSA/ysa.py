from qsfilemaker import QSLine, WDID
import argparse
import rdflib
import datetime

'''
class YSAEntry(object):

    def __init__(self, label):
        self.label = label


g = rdflib.Graph()
g.parse('ysa-skos.ttl', format='turtle')

for i, (subject, predicate, obj) in enumerate(g.subjects()):
    print(subject)
    print(predicate)
    print(obj)
    print()
    if i > 9:
        break
'''

def get_id(url):
    return url.split('/')[-1]

def parse_tyyppitieto(s):
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kylä, kaupunginosa tai kulmakunta'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Vakavesi'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kunta, maaseutu'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Saari'
    return s.split(';')[-1]



def get_current_date():
    # +2017-10-04T00:00:00Z/11
    return datetime.datetime.today().strftime('+%Y-%m-%dT00:00:00Z/11')

def get_wikidata_links(filepath='ysa-skos.ttl'):
    g = rdflib.Graph()
    g.parse(filepath, format='turtle')

    qres = g.query(
        """SELECT ?a ?alabel ?closeMatch ?exactMatch
           WHERE {
              ?a skos:closeMatch ?closeMatch .
              ?a skos:prefLabel ?alabel .
              FILTER(STRSTARTS(STR(?closeMatch), 'http://www.wikidata.org/entity/'))
              OPTIONAL {
                  ?a skos:exactMatch ?exactMatch .
                  FILTER(STRSTARTS(STR(?exactMatch), 'http://www.yso.fi/onto/yso/'))
              }
           }""")

    count = 0
    for row in qres:
        line = QSLine(WDID.get_validated_qid(row[2]))
        line.add_string_to_line('P6293', get_id(row[0]))
        line.add_string_to_line('P1810', row[1])
        line.line += QSLine.TAB + 'S248' + QSLine.TAB + 'Q5409964'
        line.line += QSLine.TAB + 'S6293' + QSLine.TAB + '"' + get_id(row[0]) + '"'
        line.line += QSLine.TAB + 'S813' + QSLine.TAB + get_current_date()
        print(line.line)
        count += 1

        if not row[3]:
            continue

        '''
        try:
            row[3]
        except IndexError:
            continue
        '''

        line = QSLine(WDID.get_validated_qid(row[2]))
        line.add_string_to_line('P2347', get_id(row[3])[1:])
        line.line += QSLine.TAB + 'S248' + QSLine.TAB + 'Q5409964'
        line.line += QSLine.TAB + 'S6293' + QSLine.TAB + '"' + get_id(row[0]) + '"'
        line.line += QSLine.TAB + 'S813' + QSLine.TAB + get_current_date()
        print(line.line)
    print(count)

get_wikidata_links()
