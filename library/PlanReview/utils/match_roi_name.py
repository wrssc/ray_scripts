import re
from typing import Iterable, List, Optional

def match_roi_name(
    roi_names: Iterable[str],
    roi_list: Iterable[str],
    mode: str = "exact",
    case_sensitive: bool = False,
    pattern: Optional[str] = None
) -> List[str]:
    """
    Match ROI names using exact, contains, or regex modes.

    Args:
        roi_names: Iterable of query names.
        roi_list: Iterable of ROI names available in the case.
        mode: "exact", "contains", or "regex".
        case_sensitive: If False, match case-insensitively.
        pattern: Optional raw regex to use when mode == "regex".
            If provided, roi_names is ignored.

    Returns:
        List of matching ROI names (unique, preserving roi_list order).
    """
    flags = 0 if case_sensitive else re.IGNORECASE

    # Build regex pattern
    if mode == "regex":
        if pattern is None:
            raise ValueError("pattern must be provided when mode='regex'")
        regex = re.compile(pattern, flags)

    elif mode == "exact":
        # ^name$ OR ^(name1|name2|...)$
        escaped = [re.escape(n) for n in roi_names]
        regex = re.compile(r"^(%s)$" % "|".join(escaped), flags)

    elif mode == "contains":
        # substring match
        escaped = [re.escape(n) for n in roi_names]
        # (name1|name2|...)
        regex = re.compile(r"(%s)" % "|".join(escaped), flags)

    else:
        raise ValueError(f"Unsupported mode: {mode}")

    out = []
    seen = set()
    for roi in roi_list:
        if roi not in seen and regex.search(roi):
            out.append(roi)
            seen.add(roi)

    return out
