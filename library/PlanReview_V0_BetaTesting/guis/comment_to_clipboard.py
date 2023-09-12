import tkinter as tk
from ..utils.get_approval_info import get_approval_info


def comment_to_clipboard(rso):
    # Clear the system clipboard
    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()

    # Create the beamset comment
    approval_status = get_approval_info(rso.plan, rso.beamset)
    beamset_comment = approval_status.beamset_approval_time

    # Copy the comment to the system clipboard
    root.clipboard_append(beamset_comment)
    root.update()

    # Return the root window so it can be destroyed by the caller
    return root
