class Bug_Report:

	def __init__(self, description, error_output, files: list = []):
		self.description = description
		self.error_output = error_output
		self.files = files

	def get_error_output(self):
		return self.error_output

	def get_bug_description(self):
		return self.description

	def get_files(self):
		return self.files if self.files else []

	def set_error_output(self, error_output):
		self.error_output = error_output

	def set_bug_description(self, description):
		self.description = description

	def get_report(self):
		return f'Bug Description: \n' + \
					self.get_bug_description() + f'\n\n' + \
					'AI Response: \n' + \
					self.get_error_output() + f'\n\n'
