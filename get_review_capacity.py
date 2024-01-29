#!/usr/bin/env python3
"""
Example script for working with the ARR/OpenReview API
    Gets reviewer/AC capacity based on max load 
"""

import openreview
from collections import defaultdict


def get_max_load(client1, venue1, member_role):

    group_members = client1.get_group(f"{venue1}/{member_role}").members
    print(f"{member_role} - Total number of members in system: {len(group_members)}")
    max_load = {}
    distribution = defaultdict(int)
    total_capacity = 0
    for count, member in enumerate(group_members):
        # NOTE: this invitation may need to be adjusted based on your venue. It might not be called "Custom_Max_Papers"
        edge_max_load = client1.get_edges(invitation=f"{venue1}/{member_role}/-/Custom_Max_Papers", tail=member)
        if edge_max_load is not None and len(edge_max_load)>0:
            max_load[member] = edge_max_load[0].weight
            total_capacity += max_load[member]
            distribution[max_load[member]] += 1
        else:
            print("    No edge, skipping", member)
            continue

    print(f"{member_role} - Number of members who set max load for this cycle: {len(max_load)}")
    print(f"{member_role} - Total capacity: {total_capacity} reviews")
    num_active_member = 0
    for i in sorted(distribution.keys()):
        print(f"  #members who set max load to {i}: {distribution[i]}")
        if i != 0:
            num_active_member += distribution[i]
    print(f"{member_role} - Number of active members: {num_active_member}\n")

    return max_load

if __name__ == '__main__':

    # 1. User-specific settings
    username1=input('Enter OpenReview username: ')
    password1=input('Enter password: ')
    venue1=input('Enter venue, e.g., aclweb.org/ACL/ARR/2023/December : ')
    baseurl1='https://api.openreview.net'

    # 2. Setup OpenReview client
    client1 = openreview.Client(baseurl=baseurl1, username=username1, password=password1)

    # 3. Get max load
    ac_max_load = get_max_load(client1, venue1, 'Area_Chairs')
    reviewer_max_load = get_max_load(client1, venue1, 'Reviewers')
