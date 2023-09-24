# TWO GUI's for PEER & Admin

# Graphic modules (Whole point of this file)
import tkinter as tk

from PIL import Image
import tkinter.ttk as ttk
import customtkinter as ctk

# File handling modules and OS modules (For specific problems) - CONVERT_ICON.
import os
from pathlib import Path
from tkinter import filedialog


def convert_ICON(pic: str):
    """
    Function that returns the ICON path of the icon_name file.
    :param pic:
    :return:
    """

    dot_index = pic.index('.')
    ending = pic[dot_index:]

    # Get the parent directory of the current script
    root_dir = Path(__file__).resolve().parents[1]

    # Search for every icon.
    for icon_path in root_dir.glob(f"**/gui/*{ending}"):
        if icon_path.name == pic:
            return str(icon_path)

    # Icon not found.
    return ""

class Admin_GUI:
    LOGO_PATH: str = convert_ICON(r"torrent_icon.ico")

    def __init__(self):
        """
        A function that BUILDS the GUI.
        :return:
        """

        self.window = ctk.CTk()
        self.window.configure(fg_color='#201E20')
        self.window.iconbitmap(Admin_GUI.LOGO_PATH)
        self.window.title("sTorrent")

        # Set window sizes.
        full_width = int(self.window.winfo_screenwidth())
        full_height = int(self.window.winfo_screenheight())
        width = int(full_width // 1.5)
        height = int(full_height // 1.5)
        self.window.geometry(f'{width}x{height}')

        # Responsive GUI.
        self.window.rowconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        self.window.rowconfigure(2, weight=1)

        self.window.columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            master=self.window,
            text='sTorrent Admin Panel',
            compound='center',
            text_color='#E0A96D',
            font=('Arial', 35, 'bold'),
        )
        header.grid(row=0, column=0, sticky='news')
        # General data.
        self.general_data_frame = ctk.CTkFrame(
            master=self.window,
            fg_color='#201E20'
        )
        self.general_data_frame.grid(row=1, column=0, sticky='new')

        # General data labels.
        self.users = ctk.CTkLabel(
            master=self.general_data_frame,
            fg_color='#201E20',
            text='Online peers: ',
            text_color='#DDC3A5',
            compound='center',
            font=('Arial', 15, 'bold'),
        )
        self.users.grid(row=0, column=0, ipadx=40, sticky='news')

        # Average transfer size.
        self.avg_transfer_size = ctk.CTkLabel(
            master=self.general_data_frame,
            fg_color='#201E20',
            text='Average transfer size: ',
            text_color='#DDC3A5',
            compound='center',
            font=('Arial', 15, 'bold'),
        )
        self.avg_transfer_size.grid(row=0, column=1, ipadx=40, sticky='news')

        # Log in.
        self.log = ctk.CTkLabel(
            master=self.general_data_frame,
            fg_color='#201E20',
            text='Opened at: ',
            text_color='#DDC3A5',
            compound='center',
            font=('Arial', 15, 'bold'),
        )
        self.log.grid(row=0, column=2, ipadx=40, sticky='news')

        for i in range(3):
            self.general_data_frame.columnconfigure(i, weight=1)

        self.general_data_frame.rowconfigure(0, weight=1)

        # ----------------------------- TABLE -----------------------------

        # Custom Style
        style = ttk.Style()
        style.theme_use('clam')

        # Configure Treeview style
        style.configure("Custom.Treeview.Treeview",
                        background="white",
                        fieldbackground="white",
                        foreground="black",
                        rowheight=30,
                        highlightthickness=0,
                        borderwidth=0,
                        font=('Arial', 12),
                )

        self.tree_frame = ctk.CTkFrame(
            master=self.window,
        )
        self.tree_frame.grid(row=2, column=0, pady=0, sticky='news')

        displayed_database = {
            'col_status': 'Status',
            'col_name': 'Name',
            'col_shares': 'Shares'
        }
        self.tree = ttk.Treeview(
            master=self.tree_frame,
            columns=tuple(displayed_database.keys()),
            show='headings',
            style='Custom.Treeview',
        )

        for col, header in displayed_database.items():
            self.tree.heading(col, text=header, anchor=tk.CENTER)

        for column in range(1, 4):
            self.tree.column(f"#{column}", anchor=tk.CENTER)

        # Adjustments.
        self.tree_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)

        style.map("Custom.Treeview.Treeview",
                  background=[("selected", "lightblue")],
                  foreground=[("selected", "black")])

        # Apply styles
        self.tree.configure(style="Custom.Treeview.Treeview")
        self.tree.grid(row=0, column=0, sticky='news')

    def update_tree(self, document: dict):

        # do the action.
        if document['action'] == 'insert':

            self.tree.insert(
                parent='', index='end', values=tuple(document.values())[1:]
            )

            children = self.tree.get_children()
            self.users.configure(text=self.users.cget("text")[0: 14] + str(len(children)))

        elif document['action'] == 'update':

            children = self.tree.get_children()
            rows = [child for child in children if self.tree.item(child)["values"][1] == document['name']]

            if rows:

                # Update the row
                update_id = rows[0]
                update_values = list(document.values())[1:]
                previous_parts = update_values.pop() + ", "
                update_values.append(previous_parts + self.tree.item(update_id)["values"][2])

                # Update the TREE
                self.tree.item(update_id, text='', values=update_values)

    def delete_peer(self, name):

        children = self.tree.get_children()
        rows = [child for child in children if self.tree.item(child)["values"][1] == name]

        if rows:
            delete_id = rows[0]
            self.tree.delete(delete_id)
            self.users.configure(text=self.users.cget("text")[0: 14] + str(len(children) - 1))


class Peer_GUI:

    LOGO_PATH: str = convert_ICON(r"torrent_icon.ico")

    def __init__(self, name, controller):
        """
        A function that BUILDS the GUI.
        :return:
        """

        self.name = name
        self.controller = controller

        self.progress_bars = dict([])

        self.window = ctk.CTk()
        self.window.iconbitmap(Peer_GUI.LOGO_PATH)
        self.window.title("Torrent Client")

        # Set up colors
        bg_color = "#0E1726"  # Dark blue
        fg_color = "#FFFFFF"  # White
        highlight_color = "#3F82DA"  # Bright blue

        # Set up window size and position
        self.window.geometry("800x600")

        # Set up styles
        style = ttk.Style()
        style.theme_use("clam")

        # Configure style for buttons
        style.configure(
            "DarkBlue.TButton",
            foreground=fg_color,
            background=bg_color,
            font=("Arial", 12),
            highlightbackground=highlight_color,
            highlightthickness=2,
        )

        self.page_one = ctk.CTkFrame(master=self.window)

        # Create a label with a modern font
        font = ctk.CTkFont(family='Arial', size=30, slant='italic', weight='bold')
        self.label = ctk.CTkLabel(
            self.page_one,
            text=f"Torrent Client\n{self.name}",
            font=font
        )
        self.label.grid(row=0, column=0, sticky='nes')

        img = Image.open(convert_ICON('LOGO.png'))
        logo = ctk.CTkImage(img, size=(300, 300))
        self.logo = ctk.CTkLabel(self.page_one, text='', image=logo, corner_radius=30)
        self.logo.grid(row=0, column=1, sticky='nws')

        # Create a frame for the file section
        self.file_frame = ctk.CTkFrame(self.page_one)
        self.file_frame.grid(row=1, column=0, pady=10, padx=10, sticky='news')

        # Create a label for the file section
        self.files_header = ctk.CTkLabel(
            self.file_frame,
            text="Select a file to download",
            font=("Arial", 12, "bold")
        )
        self.files_header.grid(row=0, column=0, sticky='nes')

        img = ctk.CTkImage(Image.open(convert_ICON('reload.png')), size=(30, 30))
        self.reload_button = ctk.CTkButton(
            self.file_frame,
            text='',
            image=img,
            command=lambda: self.reload_button_clicked(),
            width=20,
            height=20,
        )
        self.reload_button.grid(row=0, column=1)

        # Create a listbox for the files
        self.download_list_box = tk.Listbox(
            self.file_frame, font=("Arial", 12), fg=fg_color, bg=bg_color
        )
        self.download_list_box.grid(row=1, column=0, columnspan=2, sticky="news")

        # Create a frame for the info section
        self.info_frame = ctk.CTkFrame(self.page_one)
        self.info_frame.grid(row=1, column=1, pady=10, padx=10, sticky='news')

        # Create a label for the info section
        info_label = ctk.CTkLabel(
            self.info_frame,
            text="Network logger",
            font=("Arial", 12, "bold")
        )
        info_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.info_list_box = tk.Listbox(
            self.info_frame, font=("Arial", 12), fg=fg_color, bg=bg_color, selectmode='SINGLE'
        )
        self.info_list_box.grid(row=1, column=0, columnspan=2, sticky='news')

        self.button_frame = ctk.CTkFrame(self.page_one)
        self.button_frame.grid(row=2, column=0, pady=10, padx=10, columnspan=2, sticky='ew')

        # Create the Upload button
        self.upload_button = ctk.CTkButton(
            self.button_frame,
            text="Upload File",
            font=("Arial", 12, 'bold'),
            command=lambda: self.upload_button_clicked(),
        )
        self.upload_button.grid(row=0, column=0, padx=10, sticky='ew')

        # Create the Download button
        self.download_button = ctk.CTkButton(
            self.button_frame,
            text="Download File",
            font=("Arial", 12),
            command=lambda: self.download_button_clicked()
        )
        self.download_button.grid(row=0, column=1, padx=10, sticky='ew')

        # Create the Download button
        self.current_downloads = ctk.CTkButton(
            self.button_frame,
            text="My Downloads",
            font=("Arial", 12),
            command=lambda: self.show_downloads()
        )
        self.current_downloads.grid(row=0, column=2, padx=10, sticky='ew')

        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.columnconfigure(1, weight=1)
        self.button_frame.columnconfigure(2, weight=1)

        for i in range(3):
            self.page_one.rowconfigure(i, weight=1)
            self.file_frame.rowconfigure(i, weight=1)
            self.info_frame.rowconfigure(i, weight=1)

        for i in range(2):
            self.page_one.columnconfigure(i, weight=1)
            self.file_frame.columnconfigure(i, weight=1)
            self.info_frame.columnconfigure(i, weight=1)

        self.file_frame.columnconfigure(1, weight=1)

        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        # ---------------------- DOWNLOADS ------------------

        self.downloads_page = ctk.CTkFrame(master=self.window)
        self.progress_bars_frame = ctk.CTkScrollableFrame(master=self.downloads_page)
        self.progress_bars_frame.grid(row=0, column=0, sticky='news')

        self.main_button = ctk.CTkButton(master=self.downloads_page, text='Back to main', command=lambda: self.show_main())
        self.main_button.grid(row=1, column=0)

        self.downloads_page.rowconfigure(0, weight=1)
        self.downloads_page.columnconfigure(0, weight=1)

        self.show_main()

    def open_progress_bar(self, file_name, inc, full_size):

        """
        Opens a new progress bar OR updates existing one.
        :param full_size:
        :param file_name:
        :param inc:
        :return:
        """

        print(self.progress_bars)
        print(f"INC IS: {inc} FULL SIZE IS: {full_size}")

        if file_name not in tuple(self.progress_bars.keys()):

            print("Creating progress!")

            file_button = ctk.CTkLabel(master=self.progress_bars_frame, text=f"Downloading {file_name}...")
            file_button.pack()

            style = ttk.Style()
            style.configure("Custom.Horizontal.TProgressbar",
                            background='#00cc44'
                            )

            progress_bar = ttk.Progressbar(
                self.progress_bars_frame,
                value=0,
                maximum=full_size,
                mode='determinate',
                orient='horizontal',
                style="Custom.Horizontal.TProgressbar"
            )

            progress_bar.pack(fill=tk.X, ipady=10)
            self.progress_bars.update({file_name: {file_button: progress_bar}})
            print(f"Objects for {file_name} - {self.progress_bars}")

            # case where it's small.
            if inc >= full_size:

                print(f"Completing download {inc} - {full_size}")

                temp_size = full_size
                inc = temp_size // 5
                while temp_size > 0:
                    progress_bar["value"] += inc
                    self.progress_bars_frame.update_idletasks()
                    temp_size -= inc
            else:

                print(f"Increasing lower inc {inc}")
                progress_bar["value"] += inc
                self.progress_bars_frame.update_idletasks()

        else:

            print(f"Increasing in parts! {inc}")
            progress_bar = tuple(self.progress_bars[file_name].values())[0]
            if progress_bar["value"] < full_size:
                print("ADDITION")
                progress_bar['value'] += inc
                self.progress_bars_frame.update_idletasks()

        value = progress_bar["value"]
        print(f"VALUE: {value}")

        if progress_bar['value'] >= full_size:

            print("GOT!")
            file_label = tuple(self.progress_bars[file_name].keys())[0]
            file_label.configure(text=f"File: {file_name} has been downloaded")

    def show_main(self):
        """
        Back to the main page.
        :return:
        """
        self.downloads_page.grid_forget()
        self.page_one.grid(row=0, column=0, sticky='news')

    def show_downloads(self):
        """
        Goes to the downloads page.
        :return:
        """
        self.page_one.grid_forget()
        self.downloads_page.grid(row=0, column=0, sticky='news')

    def reload_button_clicked(self):
        """
        Updates download list box.
        :return:
        """
        self.download_list_box.delete(0, tk.END)
        for i in set(self.controller.on_network_files()):
            self.download_list_box.insert(tk.END, i)

    def update_list(self, line):

        """
        Updates info list box (Logger)
        :param line:
        :return:
        """

        self.info_list_box.insert(0, line)

    def upload_button_clicked(self):

        file_path = tk.filedialog.askopenfilename(
            initialdir=os.getcwd(),
            title='Upload file to network',

        )
        if file_path:
            # Parse it to the MODUL.
            self.controller.parse_files_to_modul(file_path)

    def download_button_clicked(self):
        """
        Allows selection from the list -> parses it in order to download.
        :return:
        """
        try:
            selection = self.download_list_box.get(self.download_list_box.curselection())
        except:
            return
        if selection:
            self.controller.parse_files_to_download(selection)

