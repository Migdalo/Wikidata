
import rdflib
import sys

g = rdflib.Graph()
g.parse('cn-skos.ttl', format='turtle')

def parse_tyyppitieto(s):
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kylä, kaupunginosa tai kulmakunta'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Vakavesi'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kunta, maaseutu'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Saari'
    return s.split(';')[-1]


def check(url):
    if url.startswith('http://urn.fi/URN:NBN:fi:au:cn:'):
        return url.split('http://urn.fi/URN:NBN:fi:au:cn:')[1]
    else:
        return None


qres = g.query(
    """SELECT DISTINCT ?a ?alabel
       WHERE {
          ?a skos:prefLabel ?alabel .
       }""")

'''
for row  in qres:
    if not check(row[0]):
        print(row)

sys.exit()
'''

tmp = '1234567890'
shortest = (tmp, len(tmp))
longest = ('A', 1)

for row in qres:
    #print(row)
    s = check(row[0])
    if not s:
        continue
    if len(s) > longest[1]:
        longest = (s, len(s))
    elif len(s) < shortest[1]:
        shortest = (s, len(s))

print(len(qres))

print('Shortest:', shortest)
print('Longest:', longest)





































##################################
#######   OLD   ##################
##################################





def query1():
    qres = g.query(
        """SELECT DISTINCT ?broader ?broaderlabel
           WHERE {
              ?a skos:broader ?broader .
              ?broader skos:prefLabel ?broaderlabel .
              FILTER NOT EXISTS {
                ?a a ysa-meta:GeographicalConcept .
              }
              FILTER NOT EXISTS {
                ?broader skos:broader [] .
              }
           }""")
   #return qres
