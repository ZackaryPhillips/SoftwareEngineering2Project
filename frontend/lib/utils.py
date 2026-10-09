from pathlib import Path

class fileManager:

	filename = None	

	def __init__(self, filename):
		self.filename = filename		

	def write(self, file_contents):
		fout = open(self.filename, 'a')
		fout.write(file_contents + '\n')
		fout.close()

	def read(self):
		fin = open(self.filename, 'r')
		file_contents = fin.read()
		fin.close()
		return file_contents