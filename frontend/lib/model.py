class Bug_Report:

	def __init__(self, description, error_output='', files: list = None):
		self.description = description
		self.error_output = error_output	# error message / stack trace from the user
		self.files = list(files) if files else []	# paths of attached source files
		self.bug_id = None			# assigned by the backend on submit
		self.ai_response = ''
		self.decision = None		# 'accept' or 'reject' once the user has reviewed the fix

	def get_error_output(self):
		return self.error_output

	def get_bug_description(self):
		return self.description

	def get_files(self):
		return self.files

	def get_bug_id(self):
		return self.bug_id

	def get_ai_response(self):
		return self.ai_response

	def get_decision(self):
		return self.decision

	def set_error_output(self, error_output):
		self.error_output = error_output

	def set_bug_description(self, description):
		self.description = description

	def set_bug_id(self, bug_id):
		self.bug_id = bug_id

	def set_ai_response(self, ai_response):
		self.ai_response = ai_response

	def set_decision(self, decision):
		self.decision = decision

	def get_report(self):
		return f'Bug Description: \n' + \
					self.get_bug_description() + f'\n\n' + \
					'AI Response: \n' + \
					self.get_ai_response() + f'\n\n'
