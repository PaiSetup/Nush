import glob
import itertools

# Fetching

def fetch_root_directory():
	return input("Provide root directory: ")

def fetch_extensions():
	raw = fetch_raw_extensions()
	extensions = process_extensions(raw)
	return extensions
	
def fetch_raw_extensions():
	return input("Provide extensions of files to search for: ")
	
def process_extensions(raw):
	result = raw.split(sep=' ')
	for i in range(len(result) - 1, -1 , -1):
		while result[i].startswith('.'):
			result[i] = result[i][1:]
		if result[i] is '':
			del(result[i])
	return result
	
def fetch_recursive():
	raw = input("Recursive search (Y/N): ")
	raw = raw.strip()
	return raw == 'y' or raw == 'Y'
	
	
# Counting
	
def get_files(root, extensions, recursive):
	if bool(recursive):
		file_generators = [glob.iglob('{}/**/*.{}'.format(root, x), recursive=True) for x in extensions]
	else:
		file_generators = [glob.iglob('{}/*.{}'.format(root, x)) for x in extensions]
	files = itertools.chain(*file_generators)
	return files
		
def count_lines(files):
	def count(file):
		lines, empty_lines = 0,0
		try:
			print(file)
			with open(file) as f:
				for line in f:
					lines += 1
					if line.strip() is '':
						empty_lines += 1
		except OSError:
			lines, empty_lines = 0,0
		return lines, empty_lines
		
	def sum_tuples(args):
		return ([sum(x) for x in zip(*args)])



	count_results = [count(file) for file in files]
	return sum_tuples(count_results)
	

	
	
	
# Output

def printOutput(lines, empty_lines):
	print('{} lines\n{} empty lines'.format(lines, empty_lines))
	input()

	
# Main

def main():
	root = fetch_root_directory()
	extensions = fetch_extensions()
	recursive = fetch_recursive()
	
	files = get_files(root, extensions, recursive)
	result = count_lines(files)
	
	printOutput(*result)
	
if __name__ == '__main__':
	main()
	