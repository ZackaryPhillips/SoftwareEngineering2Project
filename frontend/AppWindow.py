import tkinter as tk
from tkinter import messagebox, filedialog
from queue import Empty, Queue
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
        file_button_frame = tk.Frame(file_frame)
        file_button_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        tk.Button(file_button_frame, text="Attach files", command=self.retrieve_file).pack(side="left", padx=5)
        tk.Button(file_button_frame, text="Clear files", command=self.clear_files).pack(side="left", padx=5)

        button_frame = tk.Frame(bug_description_frame)
        button_frame.grid(row=1, column=0, pady=5)        
        tk.Button(button_frame, text="Submit bug", command=self.submit_bug).pack(side="left", padx=5)

        self.attached_file = []
        self.root = root
        self.ui_updates = Queue()
        self.history_entries = {}
        self.submission_count = 0
        root.after(50, self._process_ui_updates)
        root.mainloop()

    # ---------------- interaction ----------------

    def submit_bug(self):

        the_bug = Bug_Report('', '', self.attached_file)        

        the_bug.set_bug_description(self.entry_bug_description.get('1.0', 'end').strip())
        if not the_bug.get_bug_description():
            messagebox.showwarning("Empty", "Please describe the bug first.")
            return

        self.submission_count += 1
        history_id = f"submission-{self.submission_count}"
        description = the_bug.get_bug_description()
        self.update_history(history_id, description, "Submitting...")
        self.set_status("Submitting bug...")

        # Network calls run in a background thread so the UI stays responsive.
        Thread(
            target=self._process_bug,
            args=(description, the_bug, history_id),
            daemon=True,
        ).start()

    def _process_bug(self, description: str, the_bug: Bug_Report, history_id: str):
        try:
            the_bug.set_bug_id(post_bug(the_bug))
        except Exception as e:
            self.ui_updates.put(
                lambda error=e: self.finish_failed_submission(
                    history_id, description, error
                )
            )
            return

        self.ui_updates.put(
            lambda: self.mark_diagnosis_pending(history_id, description)
        )
        try:
            the_bug.set_ai_response(get_AI_response(the_bug.get_bug_id()))
        except Exception as e:
            self.ui_updates.put(
                lambda error=e: self.finish_failed_diagnosis(
                    history_id, description, error
                )
            )
            return
        self.ui_updates.put(
            lambda: self.finish_submission(the_bug, description, history_id)
        )

    # ---------------- helpers ----------------

    def _process_ui_updates(self):
        self.root.after(50, self._process_ui_updates)
        while True:
            try:
                update = self.ui_updates.get_nowait()
            except Empty:
                break
            update()

    @staticmethod
    def _submission_error_message(error: Exception) -> str:
        return (
            f"Request failed: {error}\n\n"
            "Please try a debugging-focused report that includes:\n"
            "- What you expected to happen\n"
            "- What actually happened\n"
            "- Steps or input to reproduce the problem\n"
            "- The relevant code and full error message or traceback"
        )

    def finish_failed_submission(
        self, history_id: str, description: str, error: Exception
    ):
        self.update_history(history_id, description, f"Submission failed: {error}")
        self.show_submission_error(self._submission_error_message(error))

    def show_submission_error(self, message: str):
        self.set_status("Request failed. Your description was kept so you can edit and retry.")
        messagebox.showerror("Request failed", message)

    def mark_diagnosis_pending(self, history_id: str, description: str):
        self.update_history(history_id, description, "Diagnosis pending...")
        self.set_status("Report submitted; waiting for AI diagnosis...")

    def finish_failed_diagnosis(
        self, history_id: str, description: str, error: Exception
    ):
        self.update_history(history_id, description, f"Diagnosis failed: {error}")
        self.show_submission_error(self._submission_error_message(error))

    def finish_submission(
        self, the_bug: Bug_Report, description: str, history_id: str
    ):
        self.update_history(history_id, description, the_bug.get_ai_response())
        self.load_AI_response(the_bug)
        if self.entry_bug_description.get('1.0', 'end').strip() == description:
            self.entry_bug_description.delete('1.0', 'end')
        if self.attached_file == the_bug.get_files():
            self.clear_files()
        self.set_status("AI response successful!")

    def load_AI_response(self, the_bug: Bug_Report):
        print('load_AI_response() method invoked')

        # sprint 3
        self.text_ai_description.config(state="normal")
        self.text_ai_description.delete('1.0', 'end')
        self.text_ai_description.config(state="disabled")

        self.text_ai_description.config(state="normal")
        self.text_ai_description.insert('end', the_bug.get_ai_response())
        self.text_ai_description.see('end')
        self.text_ai_description.config(state="disabled")

    def retrieve_file(self):
        print('retrieve_file() method invoked')
        paths = filedialog.askopenfilenames(title="Attach source files to the bug report")
        new_paths = [p for p in paths if p not in self.attached_file]
        if new_paths:
            self.attached_file.extend(new_paths)
            self.text_file_name.config(state="normal")
            self.text_file_name.insert('end', ''.join(f"{p}\n" for p in new_paths))
            self.text_file_name.see('end')
            self.text_file_name.config(state="disabled")

            print(self.attached_file)

    def clear_files(self):
        self.attached_file = []
        self.text_file_name.config(state="normal")
        self.text_file_name.delete('1.0', 'end')
        self.text_file_name.config(state="disabled")

    # sprint 3
    def update_history(self, bug_id: str, description: str, ai_response: str):
        self.history_entries[bug_id] = (
            f"Bug Description:\n{description}\n\n"
            f"AI Response:\n{ai_response}\n\n"
        )
        self.text_ai_history.config(state="normal")
        self.text_ai_history.delete('1.0', 'end')
        self.text_ai_history.insert('end', ''.join(self.history_entries.values()))
        self.text_ai_history.see('end')
        self.text_ai_history.config(state="disabled")

    def set_status(self, status_message: str):
        self.text_status_description.config(state="normal")
        self.text_status_description.delete('1.0', 'end')
        self.text_status_description.insert('end', status_message)
        self.text_status_description.see('end')
        self.text_status_description.config(state="disabled")

    