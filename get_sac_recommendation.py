#!/usr/bin/env python3
"""
Example script for download SAC recommendations from commitment site.
Note this code assume OpenReview API version 2 as well as some hardcoded 
settings on the commitment site, so you will likely need to modify it.
"""

import openreview
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Submission:
    """A paper submission, with associated assignment and review data
    Initiate by Submission(n, id, oid) where n=submission number and 
    id and original id (oid) are identifiers used internally in OpenReview
    """
    #     self.n = n 
    #     self.id = id
    #     self.oid = oid
    n: int
    id: str
    oid: str

    def __post_init__(self):
        self.ac = set()
        self.paper_status = 'undecided'
        self.meta_review = None
        self.previous_ac = {}

    def set_title(self, title):
        self.title = title

    def set_research_area(self, research_area):
        self.research_area = research_area

    def set_paper_link(self, paper_link):
        self.paper_link = paper_link
        self.paper_link_id = self.paper_link.split('=')[1].split('?')[0].replace('&noteId','')



def get_submissions_v2(client2, venue2):
    """Get submission information. Return a dictionary indexed by submission id and point to Submission objects.
    Note this code assumes openreview api version 2. 
    It also hardcodes some specific string matching based on how ARR tech copies data to the commitment site.
    You likely need to modify this function for your own commitment site. 
    """

    submissions = {}
    id2n = {}

    for note in openreview.tools.iterget_notes(client2, invitation=f"{venue2}/-/Submission", details='directReplies'):
        n = note.number
        submissions[n] = Submission(n, note.id, note.original)
        submissions[n].set_title(note.content['title']['value'])
        submissions[n].set_research_area(note.content['track']['value']) 
        submissions[n].set_paper_link(note.content['paper_link']['value'])
        id2n[note.id] = n

        metareviews =  [reply for reply in note.details["directReplies"] if reply["invitations"][0].endswith("Meta_Review")]
        for ii, mr in enumerate(metareviews):
            if mr['signatures'][0] == venue2:
                # this is previous metareview copied by ARR tech
                t = mr['content']['title']['value'].split(' ')
                month = t[5]
                previous_ac_anon = t[8]
                submissions[n].previous_ac[month] = previous_ac_anon
            else:
                # this is metareview from our NAACL SAC
                submissions[n].meta_review = mr['content']
    return submissions, id2n


def add_sac_to_papers(client2, venue2, submissions, id2n):
    area_chair_groups = ['Special_Theme',
                        'Summarization',
                        'Speech',
                        'Sentiment',
                        'Semantics_Sentence',
                        'Semantics_Lexical',
                        'Resources_Evaluation',
                        'Question_Answering',
                        'Phonology_Morphology',
                        'Applications',
                        'Multimodality',
                        'Multilinguality',
                        'Machine_Translation',
                        'Machine_Learning',
                        'Linguistic_Theories',
                        'Interpretability',
                        'Information_Retrieval',
                        'Information_Extraction',
                        'Generation',
                        'Ethics',
                        'Efficiency',
                        'Discourse',
                        'Dialogue',
                        'Social_Science',
                        'Syntax',
                        ]

    all_sac_names = set()
    print("=== Areas/Tracks and corresponding #assignments to SAC ===")
    for ac_group in area_chair_groups:
        for ac_member in client2.get_group(f"{venue2}/{ac_group}_Area_Chairs").members:
            edges = client2.get_all_edges(invitation = f"{venue2}/{ac_group}_Area_Chairs/-/Assignment", tail = ac_member)
            print(f"{ac_group}\t{ac_member}\t#assign: {len(edges)}")
            for ea in edges:
                n = id2n[ea.head]
                submissions[n].ac.add(ac_member)
                all_sac_names.add(ac_member)
    return all_sac_names


def download_sac_recommendation(filename_sac_recommendation, submissions, email, coi_papers):
    finished = 0
    not_finished_set = set()
    with open(filename_sac_recommendation, 'w') as O:
        for n, s in submissions.items():
            if n in coi_papers:
                continue
            if s.paper_status == 'undecided' and s.meta_review != None:
                if len(s.ac) > 0:
                    sac_name = list(s.ac)[0] # assumes one sac assigned to one paper
                else: # likely due to COI preventing you from getting the info or papers without assignments
                    sac_name = 'UNKNOWN' 
                meta_review_text = s.meta_review['metareview']['value'].replace('\n',' ').replace('\t', ' ')
                award_justification_text = s.meta_review['award_justification']['value'].replace('\n',' ').replace('\t', ' ')
                O.write(f"{n}\t{sac_name}\t{email[sac_name]}\t{s.research_area}\t{s.title}\t{s.meta_review['recommendation']['value']}\t{meta_review_text}\t{s.meta_review['award']['value']}\t{award_justification_text}\n")
                finished += 1
            else:
                not_finished_set.add(n)
    print(f"=== Saving SAC results in TSV file: {filename_sac_recommendation} ===\nFormat is:")
    print(f"PaperID\tSAC_name\tSAC_email\tArea\tTitle\tSAC_recommendation\tSAC_metareview\tSAC_award_suggestion\tSAC_award_justification")          
    print(f"#finished: {finished} / #not_finished: {len(not_finished_set)} ")


def get_emails(client2, ac_set):
    email = defaultdict(str)
    for m in openreview.tools.get_profiles(client2, list(ac_set)):
        if 'preferredEmail' in m.content:
            email[m.id] = m.content['preferredEmail']
        elif 'emailsConfirmed' in m.content and len(m.content['emailsConfirmed']) > 0:
            email[m.id] = m.content['emailsConfirmed'][0]
        else:
            email[m.id] = m.content['emails'][0]
    email['UNKNOWN'] ='UNKNOWN'
    print("Number of emails:", len(email))
    return email


if __name__ == '__main__':

    # 1. User-specific settings
    username2=input('Enter OpenReview username: ')
    password2=input('Enter password: ')
    venue2=input('Enter venue, e.g., aclweb.org/NAACL/2024/Conference : ')

    baseurl2='https://api2.openreview.net'
    filename_sac_recommendation = 'sac_recommendation.tsv'

    # 2. Setup OpenReview client
    client2 = openreview.Client(baseurl=baseurl2, username=username2, password=password2)

    # 3. Get submissions
    # submissions is a dictionary that stores all the Submission objects, indexed by submission number n
    # id2n is a dictionary mapping openreview ID string to submission number
    submissions, id2n = get_submissions_v2(client2, venue2)

    # 4. Populate assignments of Senior Area Chair (SAC), who are actually assigned as AC in the commitment site
    all_sac_names = add_sac_to_papers(client2, venue2, submissions, id2n)
    email = get_emails(client2, all_sac_names)

    # 5. Download SAC recommendations into TSV file
    # Set PC's COI papers here or keep it empty
    #coi_papers = set([999999,9999999])
    coi_papers = set()

    download_sac_recommendation(filename_sac_recommendation, submissions, email, coi_papers)