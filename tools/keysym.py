#!/usr/local/bin/Python

"""Displays the keysym for each KeyPress event as you type."""
import tkinter

root = tkinter.Tk()
root.title("Keysym Logger")

def reportEvent(event):
        print('keysym=%r, keysym_num=%s' % (event.keysym, event.keysym_num))
        
text  = tkinter.Text(root, width=20, height=5, highlightthickness=2)

text.bind('<KeyPress>', reportEvent)

text.pack(expand=1, fill="both")
text.focus_set()
root.mainloop()
