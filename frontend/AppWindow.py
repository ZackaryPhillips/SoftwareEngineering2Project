import tkinter as tk
from tkinter import messagebox, filedialog
from queue import Empty, Queue
from threading import Thread
from api import post_bug, get_AI_response, post_decision, relative_names
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

        # Enabled once a diagnosis is shown; the developer makes the final call on the fix.
        decision_frame = tk.Frame(ai_response_frame)
        decision_frame.grid(row=2, column=0, pady=5)
        self.button_accept = tk.Button(decision_frame, text="Accept fix", state="disabled",
                                       command=lambda: self.decide("accept"))
        self.button_accept.pack(side="left", padx=5)
        self.button_reject = tk.Button(decision_frame, text="Reject fix", state="disabled",
                                       command=lambda: self.decide("reject"))
        self.button_reject.pack(side="left", padx=5)

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
        file_frame.grid_rowconfigure(1, weight=1)
        file_frame.grid_columnconfigure(0, weight=1)
        self.label_file_count = tk.Label(file_frame, anchor="w")
        self.label_file_count.grid(row=0, column=0, columnspan=2, padx=5, sticky="ew")
        self.list_files = tk.Listbox(file_frame, width=50, height=6, selectmode="extended",
                                     activestyle="none")
        self.list_files.grid(row=1, column=0, padx=(5, 0), pady=5, sticky="nsew")
        file_scrollbar = tk.Scrollbar(file_frame, command=self.list_files.yview)
        file_scrollbar.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="ns")
        self.list_files.config(yscrollcommand=file_scrollbar.set)
        file_button_frame = tk.Frame(file_frame)
        file_button_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        tk.Button(file_button_frame, text="Attach files", command=self.retrieve_file).pack(side="left", padx=5)
        tk.Button(file_button_frame, text="Remove selected", command=self.remove_selected_files).pack(side="left", padx=5)
        tk.Button(file_button_frame, text="Clear files", command=self.clear_files).pack(side="left", padx=5)

        button_frame = tk.Frame(bug_description_frame)
        button_frame.grid(row=1, column=0, pady=5)        
        tk.Button(button_frame, text="Submit bug", command=self.submit_bug).pack(side="left", padx=5)

        self.attached_file = []
        self.root = root
        self.ui_updates = Queue()
        self.history_entries = {}
        self.submission_count = 0
        self.current_bug = None         # the bug whose diagnosis is on screen
        self.current_history_id = None
        self.refresh_file_list()
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

    def decide(self, decision: str):
        the_bug, history_id = self.current_bug, self.current_history_id
        self.set_decision_buttons("disabled")
        self.set_status("Recording your decision...")
        Thread(
            target=self._process_decision,
            args=(the_bug, history_id, decision),
            daemon=True,
        ).start()

    def _process_decision(self, the_bug: Bug_Report, history_id: str, decision: str):
        try:
            post_decision(the_bug.get_bug_id(), decision)
        except Exception as e:
            self.ui_updates.put(
                lambda error=e: self.finish_failed_decision(the_bug, error)
            )
            return
        self.ui_updates.put(
            lambda: self.finish_decision(the_bug, history_id, decision)
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
        self.current_bug, self.current_history_id = the_bug, history_id
        self.set_decision_buttons("normal")
        self.set_status("AI response successful! Review the suggested fix, then accept or reject it.")

    def finish_decision(self, the_bug: Bug_Report, history_id: str, decision: str):
        the_bug.set_decision(decision)
        label = "Accepted" if decision == "accept" else "Rejected"
        self.update_history(history_id, the_bug.get_bug_description(),
                            the_bug.get_ai_response(), decision=label)
        self.set_status(f"Suggested fix {label.lower()}.")

    def finish_failed_decision(self, the_bug: Bug_Report, error: Exception):
        # Let the user retry, unless a newer diagnosis has replaced this one on screen.
        if the_bug is self.current_bug:
            self.set_decision_buttons("normal")
        self.set_status("Your decision could not be saved. Please try again.")
        messagebox.showerror("Decision not saved", f"Request failed: {error}")

    def set_decision_buttons(self, state: str):
        self.button_accept.config(state=state)
        self.button_reject.config(state=state)

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
            self.refresh_file_list()
            self.list_files.see('end')

            print(self.attached_file)

    def remove_selected_files(self):
        selected = set(self.list_files.curselection())
        self.attached_file = [p for i, p in enumerate(self.attached_file) if i not in selected]
        self.refresh_file_list()

    def clear_files(self):
        self.attached_file = []
        self.refresh_file_list()

    def refresh_file_list(self):
        # Names are shown the same way they're sent to the AI.
        self.list_files.delete(0, 'end')
        for name in relative_names(self.attached_file):
            self.list_files.insert('end', name)
        count = len(self.attached_file)
        self.label_file_count.config(
            text=f"{count} file{'s' if count != 1 else ''} attached" if count else "No files attached"
        )

    # sprint 3
    def update_history(self, bug_id: str, description: str, ai_response: str, decision: str = ""):
        self.history_entries[bug_id] = (
            f"Bug Description:\n{description}\n\n"
            f"AI Response:\n{ai_response}\n\n"
            + (f"Decision: {decision}\n\n" if decision else "")
        )
        self.text_ai_history.config(state="normal")
        self.text_ai_history.delete('1.0', 'end')
        separator = "─" * 50 + "\n\n"
        self.text_ai_history.insert('end', separator.join(self.history_entries.values()))
        self.text_ai_history.see('end')
        self.text_ai_history.config(state="disabled")

    def set_status(self, status_message: str):
        self.text_status_description.config(state="normal")
        self.text_status_description.delete('1.0', 'end')
        self.text_status_description.insert('end', status_message)
        self.text_status_description.see('end')
        self.text_status_description.config(state="disabled")

    