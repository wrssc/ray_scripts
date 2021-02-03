""" Screen grab

"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '0.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Rendering_Settings'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'

import tkinter as tk
# from tkinter import *
from PIL import Image, ImageGrab, ImageTk
import ctypes, sys
import os

def main():

    if sys.getwindowsversion().major == 10:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # Set DPI awareness


    root = tk.Tk()
    def area_sel():
        def getPress(event): # get press position
            global press_x,press_y
            press_x,press_y = event.x,event.y

        def mouseMove(event): # movement
            global press_x, press_y, rectangleId
            fullCanvas.delete(rectangleId)
            rectangleId = fullCanvas.create_rectangle(press_x,press_y,event.x,event.y,width=5)

        def getRelease(event): # get release position
            global press_x, press_y, rectangleId
            top.withdraw()
            img = ImageGrab.grab((press_x, press_y,event.x,event.y))
            img.show()

        top = tk.Toplevel()
        top.state('zoomed')
        top.overrideredirect(1)
        fullCanvas = tk.Canvas(top)

        background = ImageTk.PhotoImage(ImageGrab.grab().convert("L"))
        fullCanvas.create_image(0,0,anchor="nw",image=background)

        # bind event for canvas
        fullCanvas.bind('<Button-1>',getPress)
        fullCanvas.bind('<B1-Motion>',mouseMove)
        fullCanvas.bind('<ButtonRelease-1>',getRelease)

        fullCanvas.pack(expand="YES",fill="both")
        top.mainloop()
        file_out=r'Q:\\RadOnc\RayStation\Reports\screenshot.jpg'
        background.write(file_out,format='jpg')

    rectangleId = None
    sel_btn = tk.Button(root, text='select area', width=20, command=area_sel)
    sel_btn.pack()

    root.mainloop()

if __name__ == '__main__':
    main()
