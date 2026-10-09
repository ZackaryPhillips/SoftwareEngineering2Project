from tkinter import *
from tkinter import messagebox, filedialog
import tkinter as tk
from api import post_bug, get_AI_response

class AppWindow:

	text_ai_description = None
	entry_bug_description = None

	def __init__(self):

		root = Tk()
		root.title("Debugging Application")
		root.geometry("1400x900")
		root.maxsize(1500, 900)
		print("reached tk instantiation")

		main_frame = Frame(root, width=1100, height=850)
		main_frame.pack(fill="both", expand="yes")
		print("main_frame created")

		ai_response_frame = LabelFrame(main_frame, text="AI Response", width=1000, height=600)
		ai_response_frame.grid(row=0, column=0, padx=5, pady=5)
		print("ai_response_frame created")

		self.text_ai_description = Text(ai_response_frame, width=150, height=30)
		self.text_ai_description.grid(row=0, column=0, padx=5, pady=5)

		bug_description_frame = LabelFrame(main_frame, text="Bug Description", width=900, height=800)
		bug_description_frame.grid(row=1, column=0, padx=5, pady=5)
		print("bug_description_frame created")

		self.entry_bug_description = Text(bug_description_frame, width=100, height=10)
		self.entry_bug_description.grid(row=0, column=0, padx=5, pady=5)

		button_bug_description = Button(bug_description_frame, text="submit bug", command=self.submit_bug)
		button_bug_description.grid(row=1, column=0, padx=5, pady=5)

		root.mainloop()

	
	def submit_bug(self):
		# placeholder for submitBug() implementation
		print('submit_bug() method invoked')
		description = self.entry_bug_description.get('1.0', 'end')
		print(f"{description}")


		# clear field
		self.entry_bug_description.delete('0.0', f"{len(description)}.0")

	def load_AI_response(self, ai_response):
		# placeholder for loadAIReponse() implementation
		print('load_AI_response() method invoked')
		self.text_ai_description.insert('1.0', ai_response)

	def retrieve_file(self):
		# placeholder for retrieve_file() implementation
		print('retrieve_file() method invoked')
