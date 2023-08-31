import re


def match_roi_name(roi_names, roi_list):
    """
    Match the structures in case witht
    Args:
        roi_names: [str1, str2, ...]: list of names to search for
        roi_list: [str1, str2, ...]: list of current rois

    Returns:
        matches: [str1, str2, ...]: list of matching rois
    """
    matches = []
    for r_n in roi_names:
        exp_r_n = r'^' + r_n + r'$'
        for m in roi_list:
            if re.search(exp_r_n, m, re.IGNORECASE):
                matches.append(m)
    return matches
