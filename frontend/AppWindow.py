import tkinter as tk
from tkinter import messagebox, filedialog
from queue import Empty, Queue
import sqlite3
from threading import Thread
from typing import Literal
import uuid
from api import post_bug, get_AI_response, post_decision, relative_names
from lib.model import Bug_Report
from history_store import HistoryStore
from TestCaseWindow import TestCaseWindow

class AppWindow:
    """GUI for a debugging assistant: describe a bug, get an AI diagnosis."""

    def __init__(self):
        root = tk.Tk()
        root.title("Debugging Application")
        root.geometry("1400x900")
        self.save_history_var = tk.BooleanVar(value=False)

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
        self.text_ai_description.grid(row=0, column=0, padx=(5, 0), pady=5, sticky="nsew")
        ai_scrollbar = tk.Scrollbar(ai_response_frame, command=self.text_ai_description.yview)
        ai_scrollbar.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ns")
        self.text_ai_description.config(yscrollcommand=ai_scrollbar.set)
        # Styles for the diagnosis: original code in red, the AI's replacement in green.
        self.text_ai_description.tag_configure("heading", font=("TkDefaultFont", 10, "bold"),
                                               spacing1=8, spacing3=2)
        self.text_ai_description.tag_configure("file", font=("TkDefaultFont", 10, "bold"),
                                               spacing1=6)
        self.text_ai_description.tag_configure("muted", foreground="#555555")
        self.text_ai_description.tag_configure("label_original", foreground="#a1260d",
                                               font=("TkDefaultFont", 9, "bold"), lmargin1=10)
        self.text_ai_description.tag_configure("label_replacement", foreground="#1e6b34",
                                               font=("TkDefaultFont", 9, "bold"), lmargin1=10)
        self.text_ai_description.tag_configure("code_original", font="TkFixedFont",
                                               background="#fdecea", lmargin1=10, lmargin2=10)
        self.text_ai_description.tag_configure("code_replacement", font="TkFixedFont",
                                               background="#e6f4ea", lmargin1=10, lmargin2=10)

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

        # sprint 4
        self.button_test_case = tk.Button(decision_frame, text="Request Test Case", state="disabled",
                                       command=lambda: self.show_test_case("here is a test case to help you test your application"))
        self.button_test_case.pack(side="left", padx=5)

        # -- AI response history ---
        ai_history_frame = tk.LabelFrame(main_frame, text="AI History")
        ai_history_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ai_history_frame.grid_rowconfigure(1, weight=1)
        ai_history_frame.grid_rowconfigure(2, weight=2)
        ai_history_frame.grid_columnconfigure(0, weight=1)
        tk.Checkbutton(
            ai_history_frame,
            text="Save new AI history locally",
            variable=self.save_history_var,
        ).grid(row=0, column=0, columnspan=2, padx=5, sticky="w")
        self.list_ai_history = tk.Listbox(ai_history_frame, width=60, height=10,
                                          activestyle="dotbox")
        self.list_ai_history.grid(row=1, column=0, padx=(5, 0), pady=5, sticky="nsew")
        history_scrollbar = tk.Scrollbar(ai_history_frame, command=self.list_ai_history.yview)
        history_scrollbar.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="ns")
        self.list_ai_history.config(yscrollcommand=history_scrollbar.set)
        self.list_ai_history.bind("<<ListboxSelect>>", self.show_selected_history)
        self.text_ai_history_detail = tk.Text(ai_history_frame, width=60, height=20,
                                              state="disabled", wrap="word")
        self.text_ai_history_detail.grid(row=2, column=0, columnspan=2, padx=5, pady=5,
                                         sticky="nsew")

        # --- Bug input area ---
        bug_description_frame = tk.LabelFrame(main_frame, text="Bug Description")
        bug_description_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        tk.Label(bug_description_frame, text="What's wrong?", anchor="w").grid(
            row=0, column=0, padx=5, sticky="w")
        tk.Label(bug_description_frame, text="Error output / stack trace (optional)", anchor="w").grid(
            row=0, column=1, padx=5, sticky="w")
        self.entry_bug_description = tk.Text(bug_description_frame, width=50, height=9,
                                             wrap="word")
        self.entry_bug_description.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        # Fixed-width font so tracebacks keep their indentation.
        self.entry_error_output = tk.Text(bug_description_frame, width=50, height=9,
                                          wrap="word", font="TkFixedFont")
        self.entry_error_output.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="nsew")

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
        button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        tk.Button(button_frame, text="Submit bug", command=self.submit_bug).pack(side="left", padx=5)

        self.attached_file = []
        self.root = root
        self.ui_updates = Queue()
        self.history_store = HistoryStore()
        self.history_entries = {}
        self.history_order = []
        self.history_save_flags = {}
        try:
            for entry in self.history_store.load():
                history_id = entry["id"]
                self.history_entries[history_id] = {
                    "description": entry["description"],
                    "ai_response": entry["ai_response"],
                    "decision": entry["decision"],
                }
                self.history_order.append(history_id)
                self.history_save_flags[history_id] = True
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror(
                "History could not be loaded",
                f"Saved history could not be read: {error}",
                parent=root,
            )
        self._refresh_history_list()
        self.current_bug = None         # the bug whose diagnosis is on screen
        self.current_history_id = None
        self.refresh_file_list()
        root.after(50, self._process_ui_updates)
        root.mainloop()

    # ---------------- interaction ----------------

    def submit_bug(self):

        the_bug = Bug_Report('', '', self.attached_file)

        the_bug.set_bug_description(self.entry_bug_description.get('1.0', 'end').strip())
        the_bug.set_error_output(self.entry_error_output.get('1.0', 'end').strip())
        if not the_bug.get_bug_description():
            messagebox.showwarning("Empty", "Please describe the bug first.")
            return

        history_id = uuid.uuid4().hex
        self.history_save_flags[history_id] = self.save_history_var.get()
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
            bug_id = post_bug(the_bug)
            the_bug.set_bug_id(bug_id)
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
            response = get_AI_response(bug_id)
            the_bug.set_ai_response(response["answer"])
            the_bug.set_diagnosis(response["diagnosis"])
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
            bug_id = the_bug.get_bug_id()
            if bug_id is None:
                raise RuntimeError("The bug report has not been submitted.")
            post_decision(bug_id, decision)
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
        if self.entry_error_output.get('1.0', 'end').strip() == the_bug.get_error_output():
            self.entry_error_output.delete('1.0', 'end')
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

    def set_decision_buttons(self, state: Literal["normal", "disabled"]):
        self.button_accept.config(state=state)
        self.button_reject.config(state=state)

        # sprint 4
        self.button_test_case.config(state=state)

    def load_AI_response(self, the_bug: Bug_Report):
        print('load_AI_response() method invoked')

        text = self.text_ai_description
        text.config(state="normal")
        text.delete('1.0', 'end')

        diagnosis = the_bug.get_diagnosis()
        if not diagnosis or diagnosis.get("parse_error"):
            # The AI didn't reply in the expected format: show what it said as-is.
            text.insert('end', the_bug.get_ai_response())
            if diagnosis:
                text.insert('end', "\nThe AI's reply wasn't in the expected format, "
                                   "so no suggested fix can be shown.\n", "muted")
        else:
            self._insert_diagnosis(diagnosis)

        text.see('1.0')
        text.config(state="disabled")

    def _insert_diagnosis(self, d: dict):
        text = self.text_ai_description
        text.insert('end', "Summary\n", "heading")
        text.insert('end', f"{d.get('summary', '')}\n")
        text.insert('end', f"Confidence: {d.get('confidence', 'unknown')}\n", "muted")

        text.insert('end', "Explanation\n", "heading")
        text.insert('end', f"{d.get('explanation', '')}\n")

        locations = d.get("suspected_locations", [])
        if locations:
            text.insert('end', "Where the bug is likely to be\n", "heading")
            for loc in locations:
                where = loc.get("file", "?")
                if loc.get("function"):
                    where += f" in {loc['function']}()"
                if loc.get("line"):
                    where += f", line {loc['line']}"
                text.insert('end', f"• {where}: {loc.get('reason', '')}\n")

        fixes = d.get("proposed_fix", [])
        text.insert('end', "Suggested fix\n", "heading")
        if not fixes:
            text.insert('end', "The AI didn't suggest a code change.\n", "muted")
        for fix in fixes:
            text.insert('end', f"{fix.get('file', '?')}\n", "file")
            text.insert('end', "Original\n", "label_original")
            text.insert('end', f"{fix.get('original', '').rstrip()}\n", "code_original")
            text.insert('end', "Replacement\n", "label_replacement")
            text.insert('end', f"{fix.get('replacement', '').rstrip()}\n", "code_replacement")

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

    def update_history(self, bug_id: str, description: str, ai_response: str, decision: str = ""):
        is_new = bug_id not in self.history_entries
        if is_new:
            self.history_order.append(bug_id)
        self.history_entries[bug_id] = {
            "description": description,
            "ai_response": ai_response,
            "decision": decision,
        }

        selection = self.list_ai_history.curselection()
        selected_id = self.history_order[selection[0]] if selection else None
        if is_new or selected_id is None:
            selected_id = bug_id

        if self.history_save_flags.get(bug_id, False):
            try:
                self.history_store.save(bug_id, description, ai_response, decision)
            except (OSError, sqlite3.Error) as error:
                self.history_save_flags[bug_id] = False
                self.save_history_var.set(False)
                messagebox.showerror(
                    "History could not be saved",
                    f"This report will remain available until the app closes, "
                    f"but could not be saved locally: {error}",
                    parent=self.root,
                )

        self._refresh_history_list(selected_id)

    def _refresh_history_list(self, selected_id: str | None = None):
        self.list_ai_history.delete(0, "end")
        for index, history_id in enumerate(self.history_order, start=1):
            preview = self.history_entries[history_id]["description"].replace("\n", " ").strip()
            if len(preview) > 55:
                preview = preview[:52] + "..."
            self.list_ai_history.insert("end", f"Report {index}: {preview}")

        if not self.history_order:
            return
        if selected_id not in self.history_entries:
            selected_id = self.history_order[-1]
        selected_index = self.history_order.index(selected_id)
        self.list_ai_history.selection_set(selected_index)
        self.list_ai_history.activate(selected_index)
        self.list_ai_history.see(selected_index)
        self.show_selected_history()

    def show_selected_history(self, _event=None):
        selection = self.list_ai_history.curselection()
        if not selection:
            return

        history_id = self.history_order[selection[0]]
        entry = self.history_entries[history_id]
        details = (
            f"Bug Description:\n{entry['description']}\n\n"
            f"AI Response:\n{entry['ai_response']}\n"
        )
        if entry["decision"]:
            details += f"\nDecision: {entry['decision']}\n"

        self.text_ai_history_detail.config(state="normal")
        self.text_ai_history_detail.delete("1.0", "end")
        self.text_ai_history_detail.insert("end", details)
        self.text_ai_history_detail.config(state="disabled")

    def set_status(self, status_message: str):
        self.text_status_description.config(state="normal")
        self.text_status_description.delete('1.0', 'end')
        self.text_status_description.insert('end', status_message)
        self.text_status_description.see('end')
        self.text_status_description.config(state="disabled")

    # sprint 4
    def show_test_case(self, test_case: str):

        test_case_window = TestCaseWindow(test_case)