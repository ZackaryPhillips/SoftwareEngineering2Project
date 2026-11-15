import tkinter as tk
from tkinter import messagebox, filedialog

class TestCaseWindow:    

    def __init__(self, test_case: str):
        root = tk.Tk()
        root.title("Test Case Window")
        root.geometry("1000x700")

        # --- Test Case Description Area ---
        test_case_frame = tk.LabelFrame(root, text="Test Case Description")
        test_case_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.text_test_case_description = tk.Text(test_case_frame, width=100, height=30,
                                           state="disabled", wrap="word")
        self.text_test_case_description.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.text_test_case_description.config(state="normal")
        self.text_test_case_description.insert('end', test_case)
        self.text_test_case_description.see('end')
        self.text_test_case_description.config(state="disabled")
        
        root.mainloop()

   