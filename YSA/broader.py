
import rdflib
g = rdflib.Graph()
g.parse('ysa-skos.ttl', format='turtle')

def parse_tyyppitieto(s):
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kylä, kaupunginosa tai kulmakunta'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Vakavesi'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Kunta, maaseutu'
    # 'Maanmittauslaitoksen paikannimirekisteri; tyyppitieto: Saari'
    return s.split(';')[-1]



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


qres1 = g.query(
    """SELECT DISTINCT ?a ?aname
       WHERE {
          ?a a ysa-meta:GeographicalConcept .
          ?a a ?aname .
       }""")


for row in qres1:
    print(row)

print(len(qres1))





































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
