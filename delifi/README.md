# Delifi

Deleted (wiki)link finder

## Purpose

Normally when an administrator deletes a page in one of Wikidatas sister projects,
the link will be automatically deleted from Wikidata. Sometimes this doesn't happen
due to a bug. This leads to a situation where a Wikidata item has a sitelink to a 
deleted page. 

Delifi tries to discover these bugged sitelinks, and deletes those that it finds. 


## How to run

python3 testing.py


## Architecture

* /delifi
** /delifi
*** /queries
*** /src
*** wikimedia_lang_codes.json
*** README.md
*** requirements.txt

Queries folder contains SPARQL queries that either are used by Delifi at runtime, or
were used to manually generate information Delifi needs.

All the code is located in src folder.


## Supported Wikipedia editions
Wikimedia language codes belonging to existing  Wikipedia language 
editions are saved in json form as 'wikimeida_lang_codes.json'. 
The file was generated on 12.10.2020 using a SPARQL query found at
./queries/query_wikimedia_language_codes.sprql'. 

To add support for a new Wikipedia language edition, the json file 
has to be regenerated or the new language code has to be added to 
the json file manually.


## Miscellaneous

* Wikiproject codes can contain hyphens (-). In dump filenames, they are 
  replaced with underscores (_).


## Problems

* Creation date comparison is done one page at a time. This is a problem
  if a large number of pages were created after the dump creation.
* vecwiki: sitelinks in Wikidata have namespace Modèl, but in vecwiki it's Modèlo.
  Wikipedia API query normalizes the title names:
  https://vec.wikipedia.org/w/api.php?action=query&meta=siteinfo&titles=Mod%C3%A8l:Bo
    - Also: Q26101788 nrm:Template:Chouqùette
* Q20692630

