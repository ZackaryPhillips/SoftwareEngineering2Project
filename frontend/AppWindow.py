import tkinter as tk
from tkinter import messagebox, filedialog
from threading import Thread
from api import post_bug, get_AI_response
from lib.model import Bug_Report

class AppWindow:
    """GUI for a debugging assistant: describe a bug, get an AI diagnosis."""

    def __init__(self):
        root = tk.Tk()
        root.title("Debugging Application")
        root.geometry("1400x900")

        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(0, weight=3)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # --- AI response area (read-only) ---
        ai_response_frame = tk.LabelFrame(main_frame, text="AI Response")
        ai_response_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.text_ai_description = tk.Text(ai_response_frame, width=100, height=30,
                                           state="disabled", wrap="word")
        self.text_ai_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        ai_status_frame = tk.LabelFrame(ai_response_frame, text="Status")
        ai_status_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.text_status_description = tk.Text(ai_status_frame, width=100, height=2,
                                           state="disabled", wrap="word")
        self.text_status_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # -- AI response history (read-only) ---
        ai_history_frame = tk.LabelFrame(main_frame, text="AI History")
        ai_history_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.text_ai_history = tk.Text(ai_history_frame, width=60, height= 40, 
                                       state="disabled", wrap="word")
        self.text_ai_history.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Bug input area ---
        bug_description_frame = tk.LabelFrame(main_frame, text="Bug Description")
        bug_description_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.entry_bug_description = tk.Text(bug_description_frame, width=100, height=10,
                                             wrap="word")
        self.entry_bug_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")        

        file_frame = tk.LabelFrame(main_frame, text="File Information")
        file_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.text_file_name = tk.Text(file_frame, width=50, height= 2, 
                                               state="disabled", wrap="word")
        self.text_file_name.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        tk.Button(file_frame, text="Attach file", command=self.retrieve_file).grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        button_frame = tk.Frame(bug_description_frame)
        button_frame.grid(row=1, column=0, pady=5)        
        tk.Button(button_frame, text="Submit bug", command=self.submit_bug).pack(side="left", padx=5)

        self.attached_file = []
        root.mainloop()

    # ---------------- interaction ----------------

    def submit_bug(self):

        the_bug = Bug_Report('', '', self.attached_file)        

        the_bug.set_bug_description(self.entry_bug_description.get('1.0', 'end').strip())
        if not the_bug.get_bug_description():
            messagebox.showwarning("Empty", "Please describe the bug first.")
            return

        self.entry_bug_description.delete('1.0', 'end')
        self.set_status("Submitting bug...")

        # Network calls run in a background thread so the UI stays responsive.
        Thread(target=self._process_bug, args=(the_bug.get_bug_description(), the_bug), daemon=True).start()

    def _process_bug(self, description: str, the_bug: Bug_Report):
        try:
            bug_id = post_bug(description)
            the_bug.set_error_output(get_AI_response(bug_id))
        except Exception as e:
            # tkinter isn't thread-safe: schedule UI update on the main thread
            self.text_ai_description.after(0, lambda: self.set_status(f"Error: {e}\n"))
            return
        self.text_ai_description.after(0, lambda: self.load_AI_response(the_bug))
        self.set_status("AI response successful!")       

    # ---------------- helpers ----------------

    def load_AI_response(self, the_bug: Bug_Report):
        print('load_AI_response() method invoked')

        # sprint 3
        self.text_ai_description.config(state="normal")
        self.text_ai_description.delete('1.0', 'end')
        self.text_ai_description.config(state="disabled")
        self.add_history(the_bug.get_report())

        self.text_ai_description.config(state="normal")
        self.text_ai_description.insert('end', the_bug.get_error_output())
        self.text_ai_description.see('end')
        self.text_ai_description.config(state="disabled")

    def retrieve_file(self):
        print('retrieve_file() method invoked')
        path = filedialog.askopenfilename(title="Attach a file to the bug report")
        if path:
            self.attached_file.append(path)
            self.text_file_name.config(state="normal")
            self.text_file_name.insert('end', f"{path}\n")
            self.text_file_name.see('end')
            self.text_file_name.config(state="disabled")

            print(self.attached_file)

    # sprint 3
    def add_history(self, ai_response: str):
        self.text_ai_history.config(state="normal")
        self.text_ai_history.insert('end', ai_response)
        self.text_ai_history.see('end')
        self.text_ai_history.config(state="disabled")

    def set_status(self, status_message: str):
        self.text_status_description.config(state="normal")
        self.text_status_description.delete('1.0', 'end')
        self.text_status_description.insert('end', status_message)
        self.text_status_description.see('end')
        self.text_status_description.config(state="disabled")

    