""" RayStation System Tools

    Usage: raystation_systools.py

    This script presents a number of tools to assist the planner with system-level
    tasks such as:

        1. Determine full name from reported user ID of a currently open plan.
        2. Launch Task Manager app to monitor server resources.

    This code can be improved as follows:

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Sean Frigo'
__contact__ = 'frigo@wisc.edu'
__date__ = '2025-10-20'
__version__ = '1.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__maintainer__ = 'Sean Frigo'
__email__ = 'frigo@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__credits__ = ['First credit', 'Second credit']

import tkinter as tk
from tkinter import ttk, filedialog
import subprocess, re
import os
from PIL import ImageTk, Image
import subprocess
from datetime import datetime
import pathlib

script_directory = pathlib.Path(__file__).parent.resolve()
print(script_directory)

root = tk.Tk()
root.title('RayStation System Tools')

def find_display_name():
    ''' Batch file lines
    set /p id='Enter user ID: '
    net user %id% /domain | FIND /I "Full Name"
    '''
    # user_id = 'sxf377'
    global display_name
    result_str = ''
    user_id = tab2_entry.get()
    try:
        command = ['net', 'user', user_id, '/domain']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output_string = result.stdout
        full_name_index = output_string.find('Full Name') -1
        comment_index = output_string.find('Comment') -1
        name_line = output_string[full_name_index:comment_index]
        output_fields = re.split(r'\s+', name_line) # Split using 1+ spaces as delimiter
        last_name = output_fields[3].strip(',')
        first_name = output_fields[4]
        display_name = first_name + ' ' + last_name
        result_str = 'User ID ' + user_id + "'s name is: " + display_name
        print(result_str)
    except:
        result_str = 'Entered ID not found.'
        print('Entered ID not found.')
    tab2_name_label.config(text=result_str)

def find_user_name():
    user_name = ''
    try:
        user_name = os.getenv('USERNAME')
        print('User name: ' + user_name)
    except:
        print('User name not found.')
    return user_name

def find_computer_name():
    computer_name = ''
    try:
        computer_name = os.getenv('COMPUTERNAME')
        print('Current computer name: ' + computer_name)
    except:
        print('Username not found.')
    return computer_name

def get_date_time_stamp():
    now = datetime.now(tz=None)
    dts = now.strftime('%Y%m%d%H%M%S')
    print('DTS: ' + dts)
    return dts

def start_task_manager():
    command = ['start', r'%windir%\system32\taskmgr.exe', '/7']
    try:
        result = subprocess.run(['start','taskmgr.exe'], shell=True, creationflags=subprocess.DETACHED_PROCESS)
    except:
        result = 'Process not able to start.'
        print(result)

def create_bullet_text_list(parent, data_list):
    bullet_text_widget = tk.Text(parent, wrap='word', width=80, height=3, bd=0, highlightthickness=0)
    bullet_text_widget.tag_configure('bullet', lmargin1=20, lmargin2=55, font=('Arial', 10))

    for i, item in enumerate(data_list):
        bullet_text_widget.insert(tk.END, '\u2022 ' + item + '\n', 'bullet') # Insert item text and apply tag
        # print(i, item)

    root_bg_color = root.cget('bg')
    bullet_text_widget.configure(bg=root_bg_color)
    bullet_text_widget.grid(row=1, column=0, columnspan=3, padx=20, pady=5, sticky='W')
    bullet_text_widget.config(state='disabled') # Make it read-only

def create_numbered_text_list(parent, data_list):
    text_widget2 = tk.Text(parent, wrap='word', height=3, width=80, bd=0, highlightthickness=0)
    text_widget2.tag_configure('number', lmargin1=35, lmargin2=55, font=('Arial', 10))

    for i, item in enumerate(data_list):
        text_widget2.insert(tk.END, f'{i+1}. {item}\n', 'number')
        # print(i, item)

    root_bg_color = root.cget('bg')
    text_widget2.configure(bg=root_bg_color)
    text_widget2.grid(row = 5, column=0, columnspan=3, padx=5, pady=5, sticky='W')
    text_widget2.config(state='disabled') # Make it read-only

def select_directory():
    global directory_path
    # Hide the main Tkinter window to prevent it from appearing as an empty window
    root = tk.Tk()
    root.withdraw() 
    
    # Open the directory selection dialog
    directory_path = filedialog.askdirectory(title='Select a directory').replace('/','\\')
    
    # Check if a directory was selected
    if directory_path:
        tab3_label3.config(text=directory_path)
        print(f'Selected directory: {directory_path}')
    else:
        print('No directory selected.')
    pass

def start_logging():
    pass

def stop_logging():
    pass

def load_image(filename):
    protocol_folder = r'../protocols'
    institution_folder = r'UW/Images/RayStationSystemTools'
    tab1_image_path = os.path.join(os.path.dirname(__file__),
                     protocol_folder,
                     institution_folder,
                     filename)
    return Image.open(tab1_image_path)

# Create a Notebook widget
notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

# Create frames for each tab
tab1_frame = ttk.Frame(notebook)
tab2_frame = ttk.Frame(notebook)
tab3_frame = ttk.Frame(notebook)
tab4_frame = ttk.Frame(notebook)

# Add frames to the Notebook
notebook.add(tab1_frame, text='Resources')
notebook.add(tab2_frame, text='Users')
notebook.add(tab3_frame, text='Logging')
notebook.add(tab4_frame, text='About')

# Add widgets to Tab 1
tab1_label = ttk.Label(tab1_frame, text='Observe server resources such as:') #   * System memory\n   * CPU load\n   * GPU memory')
tab1_label.grid(row=0, column=0, padx=20, pady=(20,0), sticky='W')

list_items = ['System memory', 'CPU load', 'GPU memory']
create_bullet_text_list(tab1_frame, list_items)
                          
tab1_label2 = ttk.Label(tab1_frame, text='To do so, perform the following:') #   * System memory\n   * CPU load\n   * GPU memory')
tab1_label2.grid(row=4, column=0, padx=20, pady=5, ipady=0, sticky='W')

list_items = ['Click on button below to launch the Task Manager.',
              'Click on the More details... item in the Task Manager window.',
              'Click on the Performance tab to track resources.']
create_numbered_text_list(tab1_frame, list_items)

tab1_entry_button = ttk.Button(tab1_frame, text='Start Task Manager', command=start_task_manager)
tab1_entry_button.grid(row=6,column=0, padx=20, pady=5, sticky='W')

#  Load the image
# tab1_image_path = r'H:\Home\Projects\RayStation_System_Tools\2024A\Task_Manager_Marked_Up.png'
# tab1_image_path = str(script_directory) + '\\' + 'Task_Manager_Marked_Up.png'
tab1_original_image = load_image('Task_Manager_Marked_Up.png')

# Convert to Tkinter PhotoImage
# tab1_tk_image = ImageTk.PhotoImage(tab1_original_image)

# Resize to a specific size
# tab1_resized_image = tab1_original_image.resize((200, 150), Image.LANCZOS) 

# Resize while maintaining aspect ratio (example for fitting within a certain width)
width, height = tab1_original_image.size
new_width = 500
new_height = int(new_width * (height / width))
tab1_resized_image_aspect_ratio = tab1_original_image.resize((new_width, new_height), Image.LANCZOS)
tab1_tk_image = ImageTk.PhotoImage(tab1_resized_image_aspect_ratio)

# Create a Label widget to display the image
tab1_image_label = ttk.Label(tab1_frame, image=tab1_tk_image)
tab1_image_label.grid(row=8, column=0, columnspan=3, padx=20, pady=5, sticky='W')
tab1_image_label.image = tab1_tk_image  # Important: Keep a reference to prevent garbage collection

# Add widgets to Tab 2

display_name = None

inst_text= tk.StringVar()
inst_text.set('Enter user ID. Example shown in red box below.')

inst_label = ttk.Label(tab2_frame, textvariable=inst_text)
inst_label.grid(row=0, column=0, padx=20, pady=20, sticky='W')

#  Load the image
# tab2_image_path = r'H:\Home\Projects\RayStation_System_Tools\2024A\Patient_Open_Error_Message_Marked_Up.png'  # Make sure 'example.png' is in the same directory or provide the full path
# tab2_image_path = str(script_directory) + '\\' + 'Patient_Open_Error_Message_Marked_Up.png'  # Make sure 'example.png' is in the same directory or provide the full path
# tab2_original_image = Image.open(tab2_image_path)
tab2_original_image = load_image('Patient_Open_Error_Message_Marked_Up.png')

# Convert to Tkinter PhotoImage
# tab2_tk_image = ImageTk.PhotoImage(tab2_original_image, size=200)

# Resize while maintaining aspect ratio (example for fitting within a certain width)
width, height = tab2_original_image.size
new_width = 500
new_height = int(new_width * (height / width))
tab2_resized_image_aspect_ratio = tab2_original_image.resize((new_width, new_height), Image.LANCZOS)
tab2_tk_image = ImageTk.PhotoImage(tab2_resized_image_aspect_ratio)

# Create a label widget to display the image
tab2_image_label = ttk.Label(tab2_frame, image=tab2_tk_image)
tab2_image_label.grid(row=10, column=0, columnspan=3, padx=20, pady=5, sticky='W')
tab2_image_label.image = tab2_tk_image  # Important: Keep a reference to prevent garbage collection

# Entry widget
style_noborder = ttk.Style()
style_noborder.configure("NoBorder.TEntry",
                fieldbackground="white",  # Set background color to match your window or desired color
                bordercolor="white",      # Set border color to match background to make it invisible
                lightcolor="white",
                darkcolor="white",
                relief="flat")            # Set relief to flat for no 3D effect

style_noborder.configure('NoBorder.TEntry', borderwidth=0)
tab2_entry = ttk.Entry(tab2_frame, style='Borderless.TEntry', width=30)
tab2_entry.grid(row=0, column=1, padx=20, pady=5, sticky='W')

tab2_entry_button = ttk.Button(tab2_frame, text='Get User Name', command=find_display_name)
tab2_entry_button.grid(row=4,column=0, padx=20, pady=5, sticky='W')

# Create a label widget
# The 'master' argument (root in this case) specifies the parent window/frame
# The 'text' argument sets the text displayed by the label
tab2_name_label = ttk.Label(tab2_frame, text=display_name)
tab2_name_label.grid(row=4,column=1, padx=20, pady=5, sticky='W')


# Add widgets to tab 3
app_name ='RayStation'
out_file_name = find_computer_name() + '_' + find_user_name() + '_' + app_name + '_' + get_date_time_stamp() + '.log'
# print(out_file_name)

directory_path = r'Q:\RadOnc\RayStation\Logs\Resource_Logs' 
tab3_label1 = ttk.Label(tab3_frame, text='This future tool will enable system resource logging to assist in troubleshooting.\n\n')
                                        #  'Click on the below buttons to start and stop logging.\n\n'
                                        #  'You may change the output directory prior to starting.\n\n' \
                                        #  'The filename is automatically generated.')
# tab3_label2 = ttk.Label(tab3_frame, text='Output directory: ')
# tab3_label3 = ttk.Label(tab3_frame, text=directory_path)
# tab3_label4 = ttk.Label(tab3_frame, text='Output file name: ')
# tab3_label5 = ttk.Label(tab3_frame, text=out_file_name)
tab3_label1.grid(row=0, column=0, padx=20, pady=20, sticky='W')
# tab3_label2.grid(row=2, column=0, padx=100, pady=5, sticky='W')
# tab3_label3.grid(row=2, column=0, padx=195, pady=5, sticky='W')
# tab3_label4.grid(row=3, column=0, padx=20, pady=5, sticky='W')
# tab3_label5.grid(row=3, column=0, padx=120, pady=5, sticky='W')

# tab3_button_set_dir = ttk.Button(tab3_frame, text='Set', command=select_directory)
# tab3_button_set_dir.grid(row=2,column=0, padx=20, pady=5, sticky='W')

# tab3_button_logging_start= ttk.Button(tab3_frame, text='Start', command=start_logging)
# tab3_button_logging_start.grid(row=5,column=0, padx=20, pady=5, sticky='W')

# tab3_button_logging_stop= ttk.Button(tab3_frame, text='Stop', command=stop_logging)
# tab3_button_logging_stop.grid(row=5,column=0, padx=200, pady=5, sticky='W')

# Add widgets to Tab 4
tab4_label = ttk.Label(tab4_frame, text='This collection of utilities assists users in finding RayStation system info.\n\nCreated by Sean Frigo\n\nVersion 2025-12-02')
tab4_label.grid(row=0, column=0, padx=20, pady=20)

root.mainloop()