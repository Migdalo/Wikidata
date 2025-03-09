
import rdflib
import sys

g = rdflib.Graph()
g.parse('cn-skos.ttl', format='turtle')

def is_allcaps(label):
    #return label.upper() == label
    return all([x.isupper() for x in label])

def get_agents_with_alias(alias):
    q = """SELECT DISTINCT ?a ?plabel ?alabel
           WHERE {
              ?a skos:prefLabel ?plabel .
              ?a skos:altLabel \'%s\' .
           }""" % alias
    qres = g.query(q)
    for line in qres:
        print(' * ', line)


qres = g.query(
    """SELECT DISTINCT ?a ?plabel ?alabel
       WHERE {
          ?a skos:prefLabel ?plabel .
          ?a skos:altLabel ?alabel .
       }""")

acronyms = {}
for line in qres:
    #print(line[0], line[1], line[2])
    #if 'KMK' not in line[2]:
    #    continue
    #print(line[2], is_allcaps(line[2]))
    #print(list(line[2]))
    if not is_allcaps(line[2]):
        continue
    try:
        acronyms[line[2]] += 1
    except KeyError:
        acronyms[line[2]] = 1

#print(acronyms)
for key in acronyms.keys():
    if acronyms[key] == 1:
        continue
    print(key, acronyms[key])
    get_agents_with_alias(key)


g.close()
