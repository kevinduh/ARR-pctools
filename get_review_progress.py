#!/usr/bin/env python3
"""
Example script for working with the ARR/OpenReview API
    Gets submission information from your cycle
    and reports review progress
"""

from collections import defaultdict
from dataclasses import dataclass
import openreview

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
        self.sac = set()
        self.ac = set()
        self.reviewer = set()
        self.completed_reviewer = set()
        self.preferred_conference = 'none'

    def set_title(self, title):
        self.title = title

    def populate_assignments(self, client, venue):
        self.populate_sac_assignments(client, venue)
        self.populate_ac_assignments(client, venue)
        self.populate_reviewer_assignments(client, venue)

    def populate_sac_assignments(self, client, venue):
        for ea in client.get_edges(invitation=f"{venue}/Senior_Area_Chairs/-/Assignment", head=self.id):
            self.sac.add(ea.tail)
    
    def populate_ac_assignments(self, client, venue):
        for ea in client.get_edges(invitation=f"{venue}/Area_Chairs/-/Assignment", head=self.id):
            self.ac.add(ea.tail)

    def populate_reviewer_assignments(self, client, venue):
        for ea in client.get_edges(invitation=f"{venue}/Reviewers/-/Assignment", head=self.id):
            self.reviewer.add(ea.tail)

    def mark_reviewer_completed(self, reviewer_name):
        self.completed_reviewer.add(reviewer_name)

    def set_preferred_conference(self, preferred_conference):
        self.preferred_conference = preferred_conference
    
    def set_research_area(self, research_area):
        self.research_area = research_area

    def get_completed_reviewers(self, client, venue):
        completed_reviewers = []
        try:
            group_result = openreview.tools.get_group(client, f'{venue}/Paper{self.n}/Reviewers/Submitted')
            for anon_reviewer_name in group_result.members:
                    query_result = openreview.tools.get_group(client, f'{anon_reviewer_name}')
                    completed_reviewers.append(query_result.members[0])
        except Exception as e:
            print(f"Submission.get_completed_reviewer(): Skipping {self.n}",e)
        return completed_reviewers


class Member:
    """A SAC, AC, or Reviewer, with associated paper assignments and completion status"""
    def __init__(self, name):
        self.name = name
        self.assigned = set()
        self.completed = set()
    
    def add_paper(self, submission_number):
        self.assigned.add(submission_number)
    
    def mark_paper_completed(self, submission_number):
        self.completed.add(submission_number)



def get_submissions(client1, venue1):
    """Get submission information. Return a dictionary indexed by submission id and point to Submission objects"""
    submissions = {}

    # 1. Get basic info from Blind Submissions (currently active papers)
    notes_submissions = openreview.tools.iterget_notes(client1, invitation=f"{venue1}/-/Blind_Submission")
    for note in notes_submissions:
        n = note.number
        submissions[n] = Submission(n, note.id, note.original)
        submissions[n].set_title(note.content['title'])
        submissions[n].set_research_area(note.content['research_area']) 

    print(f"Number of active submissions: {len(submissions)}")

    # 2. Extract more info from NonBlind version of Submissions
    notes_submissions_nonblind = openreview.tools.iterget_notes(client1, invitation=f"{venue1}/-/Submission")
    skipped = set()
    for note in notes_submissions_nonblind:
        n = note.number
        if n in submissions:
            if 'preferred_venue' in note.content:
                conference_name = note.content['preferred_venue'].strip().lower()
                submissions[n].set_preferred_conference(conference_name)
        else:
            skipped.add(n)

    print(f"Number of submissions withdrawn/desk-rejected: {len(skipped)}")
    return submissions

def add_paper_to_memberdict(memberdict, names, submission_number):
    """Convenience function to add paper to SAC/AC/Reviewer member dictionary"""
    for name in names:
        if name not in memberdict:
            memberdict[name] = Member(name)
        memberdict[name].add_paper(submission_number)


def get_email(client1, venue1, sac, ac, reviewer):
    """Get the emails of members in sac, ac, reviewer
    Returns a dictionary: OpenReview Profile string -> Email
    """
    sac_profiles = openreview.tools.get_profiles(client1, list(sac.keys()))
    ac_profiles = openreview.tools.get_profiles(client1, list(ac.keys()))                             
    reviewer_profiles = openreview.tools.get_profiles(client1, list(reviewer.keys()))

    email = defaultdict(str)
    for m in sac_profiles + ac_profiles + reviewer_profiles:
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
    username1=input('Enter OpenReview username: ')
    password1=input('Enter password: ')
    venue1=input('Enter venue, e.g., aclweb.org/ACL/ARR/2023/December : ')
    baseurl1='https://api.openreview.net'
    filename_urgent_papers = 'urgent_papers.tsv'
    urgent_paper_threshold = 2

    # 2. Setup OpenReview client
    client1 = openreview.Client(baseurl=baseurl1, username=username1, password=password1)

    # 3. Get submissions
    # submissions is a dictionary that stores all the Submission objects, indexed by submission number n
    submissions = get_submissions(client1, venue1)

    # 4. Populate assignments of Senior Area Chair/Editor (SAC), Area Chair/Editor (AC/AE), and Reviewer
    # sac, ac, and reviewer are dictionaries indexed by OpenReview profile string and pointing to a Member object
    sac = {}
    ac = {}
    reviewer = {}

    print("Getting SAC/AC/Reviewer assignments (this takes ~15min for ~2500 submissions)")
    count = 0
    for n, s in submissions.items():
        # populate assignments on submissions
        s.populate_assignments(client1, venue1)

        # populate same assignments on sac, ac, and reviewer side too
        add_paper_to_memberdict(sac, s.sac, n)
        add_paper_to_memberdict(ac, s.ac, n)
        add_paper_to_memberdict(reviewer, s.reviewer, n)
        count += 1
        if count % 100 == 0:
            print('.', end='')
    
    # 5. Get review completion status
    print("\nGetting Review completion status (this takes ~15min for ~2500 submissions)")
    for n, s in submissions.items():
        completed_reviewers = s.get_completed_reviewers(client1, venue1)
        try:
            for reviewer_name in completed_reviewers:
                s.mark_reviewer_completed(reviewer_name)
                reviewer[reviewer_name].mark_paper_completed(n)
        except Exception as e:
            print(f"  note - {n}: Not able to add reviewer {reviewer_name} (no profile) {e}")

    # 6. Print out summary of review completion status
    review_stats = defaultdict(int)
    urgent_papers = []
    for n, s in submissions.items():
        num_reviewed = len(s.completed_reviewer)
        review_stats[num_reviewed] += 1
        if num_reviewed <= urgent_paper_threshold:
            urgent_papers.append(n)

    for i in sorted(review_stats.keys()):
        print(f"Papers with {i} review: {review_stats[i]} ({100*review_stats[i]/len(submissions):.2f}%%)" )
    print(f"#Papers with 0 or 1 reviews: {review_stats[0] + review_stats[1]}")
    print(f"#Papers with <3 reviews: {review_stats[0] + review_stats[1] + review_stats[2]}")
    print(f"  (Note: Your COI papers will show up as having 0 reviews)")

    # 7. Get email and write out a file of SAC/AC contacts for urgent papers that need more reviews
    print(f"Check {filename_urgent_papers} for contact info for papers with <= {urgent_paper_threshold} reviews")
    email = get_email(client1, venue1, sac, ac, reviewer)

    with open(filename_urgent_papers,'w') as F:
        F.write("SubmissionID\tSAC\tSAC_email\tAC\tAC_email\t#ReviewsCompleted\n")
        for n in urgent_papers:
            num_reviewed = len(submissions[n].completed_reviewer)
            sac_name = 'UNKNOWN'
            ac_name = 'UNKNOWN'
            if len(submissions[n].sac) > 0:
                sac_name = list(submissions[n].sac)[0]
            if len(submissions[n].ac) > 0:
                ac_name = list(submissions[n].ac)[0]
            F.write(f"{n}\t{sac_name}\t{email[sac_name]}\t{ac_name}\t{email[ac_name]}\t{num_reviewed}\n")