# ARR-pctools
Simple scripts for program chairs of ARR/OpenReview reviewing

## Quickstart

First, install the OpenReview API Python client:

```
pip install openreview-py
```
Also see https://docs.openreview.net/getting-started/using-the-api/installing-and-instantiating-the-python-client


Next, try running the example script below. First you'll need to change the `venue1` string in the code to match your own. 
It will only work with venues where you have Program Chair role.

```
python get_review_capacity.py
```

This simple script will ask you for your OpenReview username/password and venue (e.g. `aclweb.org/ACL/ARR/2023/December`), then report on the max possible review capacity based on reviewer-specified max loads. 

## Scripts

These scripts are provided just for reference. They will only work with venues where you have Program Chair role.

* `get_review_capacity.py`: Check max load statistics by Reviewers and Area Chairs.
* `get_review_progress.py`: Report on the review progress for your cycle and write out papers that require urgent attention to a TSV file




## Notes

* As of the time of writing ARR using OpenReview API version 1. Other sites by default uses version 2. The `get_review_progress.py` example assumes v1.

* OpenReview API documentation: https://docs.openreview.net/overview/readme 

* General concepts that might help understand how OpenReview works: 

  1. Edges: contains head and tail, and is used to represent paper-reviewer assignment, affinity scores, custom quota, etc. 
  2. Notes: contains data and is used to represent reviews, meta reviews, decisions, paper submissions, etc.
  3. Groups: defines a list of reviewers or ACs for a paper or in general. 
  4. Invitation: not sure why it's called this, but for our purpose it roughly specifies an access point to certain data in the system, e.g.: `aclweb.org/ACL/ARR/2023/December/-/Blind_Submission` gets notes containing active submissions; `aclweb.org/ACL/ARR/2023/December/Senior_Area_Chairs/-/Assignment` gets edges containing SAC assignments; `aclweb.org/ACL/ARR/2023/December/Paper1/Reviewers/Submitted` gets the group of reviewers who submitted reviews to Paper1.
  5. For v1, each submission has two copies, one original and the other for blind review. Note they have different identifiers, i.e. `https://openreview.net/forum?id=XXXX` may differ. See https://docs.openreview.net/reference/mental-model-on-blind-submissions-and-revisions
