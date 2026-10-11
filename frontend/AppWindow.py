import tkinter as tk
from tkinter import messagebox, filedialog
from threading import Thread
from api import post_bug, get_AI_response


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
        self.text_ai_description = tk.Text(ai_response_frame, width=150, height=30,
                                           state="disabled", wrap="word")
        self.text_ai_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Bug input area ---
        bug_description_frame = tk.LabelFrame(main_frame, text="Bug Description")
        bug_description_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.entry_bug_description = tk.Text(bug_description_frame, width=100, height=10,
                                             wrap="word")
        self.entry_bug_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        button_frame = tk.Frame(bug_description_frame)
        button_frame.grid(row=1, column=0, pady=5)
        tk.Button(button_frame, text="Attach file", command=self.retrieve_file).pack(side="left", padx=5)
        tk.Button(button_frame, text="Submit bug", command=self.submit_bug).pack(side="left", padx=5)

        self.attached_file = None
        root.mainloop()

    # ---------------- interaction ----------------

    def submit_bug(self):
        description = self.entry_bug_description.get('1.0', 'end').strip()
        if not description:
            messagebox.showwarning("Empty", "Please describe the bug first.")
            return

        self.entry_bug_description.delete('1.0', 'end')
        self.load_AI_response("Submitting bug...\n")

        # Network calls run in a background thread so the UI stays responsive.
        Thread(target=self._process_bug, args=(description,), daemon=True).start()

    def _process_bug(self, description: str):
        try:
            bug_id = post_bug(description)
            answer = get_AI_response(bug_id)
        except Exception as e:
            # tkinter isn't thread-safe: schedule UI update on the main thread
            self.text_ai_description.after(0, lambda: self.load_AI_response(f"Error: {e}\n"))
            return
        self.text_ai_description.after(0, lambda: self.load_AI_response(answer))

    # ---------------- helpers ----------------

    def load_AI_response(self, ai_response: str):
        print('load_AI_response() method invoked')
        self.text_ai_description.config(state="normal")
        self.text_ai_description.insert('end', ai_response)
        self.text_ai_description.see('end')
        self.text_ai_description.config(state="disabled")

    def retrieve_file(self):
        print('retrieve_file() method invoked')
        path = filedialog.askopenfilename(title="Attach a file to the bug report")
        if path:
            self.attached_file = path
            self.load_AI_response(f"[file attached: {path}]\n")