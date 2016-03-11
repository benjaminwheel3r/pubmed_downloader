
u"""
Created on 03/03/16
by fccoelho
license: GPL V3 or Later
"""

__docformat__ = 'restructuredtext en'
from Bio import Entrez
import pymongo
import time


connection = pymongo.MongoClient()

zika_query_strings = ['((zika) NOT zika[Author])',
                 '((zika virus NOT zika[Author]))',
                 '((zika microcephaly) NOT zika[author])',
                 '((zika fever NOT zika[Author]))',
                 '(zika NOT zika[Author] ) guillain barre',
                 '((zika epidemic NOT zika[Author]))',
                 '((zika model NOT zika[Author]))',
                 '(zika NOT zika[Author] ) chikungunya',
                 '(zika NOT zika[Author] ) outbreak',
                 '(zika NOT zika[Author] ) dengue',
                 '(zika NOT zika[Author]) culex ',
                 '(zika NOT zika[Author]) mosquito',
                 '(zika NOT zika[Author])virus transmission'
                 ]
MERS_query_strings = [
    'MERS',
    'mers cov',
    'mers coronavirus',
    'mers korea',
    'mers vaccine',
    'mers camel'
]

class SearchAndCapture:
    def __init__(self, email, search_term, collection='articles'):
        self.search_term =search_term
        Entrez.email = email
        self.collection = connection.pubmed[collection]
        if collection == 'articles':
            self.citation_colection = connection.pubmed.citations
        else:
            self.citation_colection = connection.pubmed["citations_{}".format(collection)]

    def _fetch(self, pmid):
        handle = Entrez.efetch(db="pubmed", id=pmid, retmode='xml')
        records = list(Entrez.parse(handle))
        return records

    def _get_old_ids(self):
        oldids = self.collection.find({}, {"MedlineCitation.PMID": 1})
        oldids = [i['MedlineCitation']['PMID'] for i in oldids]
        return oldids

    def _get_citations(self, pmid):
        handle = Entrez.elink(dbfrom="pubmed", id=pmid, linkname="pubmed_pubmed_citedin")
        record = Entrez.read(handle)
        handle.close()
        if record[0]['LinkSetDb']:
            citers = record[0]['LinkSetDb'][0]['Link']
        else:
            citers = []
        return [i['Id'] for i in citers]

    def update_citations(self):
        print("Updating citations...")
        ids = self._get_old_ids()
        for i in ids:
            cits = self._get_citations(i)
            self.citation_colection.update_one({"PMID": i}, {"$set": {"citedby": cits}}, upsert=True)

    def update_multiple_searches(self, queries=None):
        global zika_query_strings
        if queries is not None:
            query_strings = queries
        for qs in query_strings:
            self.search_term = qs
            self.update()

    def update(self):
        old_ids = self._get_old_ids()
        print("Fetching results for {}".format(self.search_term))
        handle = Entrez.esearch(db="pubmed", retmax=1000, term=self.search_term)
        response = Entrez.read(handle=handle)
        print("Found {} items".format(len(response['IdList'])))
        new_ids = {}
        for pmid in response['IdList']:
            if pmid in old_ids:
                continue
            art = self._fetch(pmid)[0]
            result = self.collection.update_one({"MedlineCitation.PMID": art["MedlineCitation"]["PMID"]}, {"$setOnInsert": art}, upsert=True)
            new_ids[pmid] = result.upserted_id
        return new_ids



if __name__ == "__main__":
    S = SearchAndCapture('fccoelho@gmail.com', '((zika microcephaly) NOT zika[author])')
    S.update_multiple_searches()
    S.update_citations()
    T = SearchAndCapture('fccoelho@gmail.com', 'MERS', 'mers')
    T.update_multiple_searches(MERS_query_strings)
    T.update_citations()
