import tkinter as Tk
from PlanReview.utils.get_approval_info import get_approval_info
def comment_to_clipboard(rso):
    #
    # Clear the system clipboard
    r = Tk.Tk()
    r.withdraw()
    r.clipboard_clear()

    #
    # Add data to the beamset comment
    approval_status = get_approval_info(rso.plan, rso.beamset)
    beamset_comment = approval_status.beamset_approval_time
    # Copy the comment to the system clipboard
    r.clipboard_append(beamset_comment)
    r.update()  # now it stays on the clipboard after the window is closed
    return r
