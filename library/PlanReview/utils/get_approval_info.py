import xml.etree.ElementTree as ET
import pandas as pd
from dateutil import parser
from collections import namedtuple
from PlanReview.review_definitions import STAFF_XML_PATH


# Function to read XML into a DataFrame
def read_xml_to_dataframe():
    xml_path = STAFF_XML_PATH
    tree = ET.parse(xml_path)
    root = tree.getroot()

    user_data = []
    for user in root.find('users'):
        user_dict = {}
        for elem in user:
            user_dict[elem.tag] = elem.text
        user_data.append(user_dict)

    group_data = []
    for group in root.find('groups'):
        group_dict = {}
        for elem in group:
            group_dict[elem.tag] = elem.text
        group_data.append(group_dict)

    user_df = pd.DataFrame(user_data)
    group_df = pd.DataFrame(group_data)

    return user_df, group_df


# Helper function to find group name using userid
def find_groupname_by_userid(userid):
    # read in data
    user_df, group_df = read_xml_to_dataframe()
    # Convert both the DataFrame column and the input userid to lower-case
    groupcuid = user_df[user_df['userid'].str.lower() == userid.lower()]['groupcuid'].values[0]
    groupname = group_df[group_df['groupcuid'] == groupcuid]['groupname'].values[0]
    return groupname


def find_username_by_userid(userid):
    # read in data
    user_df,_ = read_xml_to_dataframe()
    # Convert both the DataFrame column and the input userid to lower-case
    user_df['userid'] = user_df['userid'].str.lower()
    match = user_df[user_df['userid'] == userid.lower()]

    if not match.empty:
        return match['username'].values[0]
    else:
        return None

def is_valid_approver(group_name, valid_approval_groups):
    return group_name.lower() in map(str.lower, valid_approval_groups)


def get_approval_info(plan, beamset):
    """
    Determine if beamset is approved and then if plan is approved. Return data
    Args:
        plan: RS plan object
        beamset: RS beamset object

    Returns:
        approval: NamedTuple.(beamset_approved, beamset_approved, beamset_exported,
                              beamset_reviewer, beamset_approval_time, plan_approved,
                              plan_exported, plan_reviewer, plan_approval_time)
    """
    Approval = namedtuple('Approval',
                          ['beamset_approved',
                           'beamset_exported',
                           'beamset_reviewer',
                           'beamset_approval_time',
                           'plan_approved',
                           'plan_exported',
                           'plan_reviewer',
                           'plan_approval_time'])
    plan_approved = False
    plan_reviewer = ""
    plan_time = ""
    plan_exported = False
    beamset_approved = False
    beamset_reviewer = ""
    beamset_time = ""
    beamset_exported = False
    try:
        if beamset.Review.ApprovalStatus == 'Approved':
            beamset_approved = True
            beamset_reviewer = beamset.Review.ReviewerName
            beamset_time = parser.parse(str(beamset.Review.ReviewTime))
            beamset_exported = beamset.Review.HasBeenExported
            if plan.Review.ApprovalStatus == 'Approved':
                plan_approved = True
                plan_reviewer = plan.Review.ReviewerName
                plan_time = parser.parse(str(plan.Review.ReviewTime))
                plan_exported = plan.Review.HasBeenExported
        else:
            plan_approved = False
            plan_reviewer = plan.Review.ReviewerName
            plan_time = parser.parse(str(plan.Review.ReviewTime))
            plan_exported = plan.Review.HasBeenExported
    except AttributeError:
        pass
    approval = Approval(beamset_approved=beamset_approved,
                        beamset_exported=beamset_exported,
                        beamset_reviewer=beamset_reviewer,
                        beamset_approval_time=beamset_time,
                        plan_approved=plan_approved,
                        plan_exported=plan_exported,
                        plan_reviewer=plan_reviewer,
                        plan_approval_time=plan_time)
    return approval
