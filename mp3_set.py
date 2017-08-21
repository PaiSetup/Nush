import eyed3
import glob


# Fetching

def fetch_directory():
	return input('Directory with mp3 files: ')
	
def fetch_recursive():
	response = input('Recursive search (Y/N): ').strip().lower()
	return response == 'y'
	
def get_files(directory, recursive):
	if bool(recursive):
		return glob.iglob('{}/**/*.mp3'.format(directory), recursive=True)
	else:
		return glob.iglob('{}/*.mp3'.format(directory))
	
def fetch_proceed(directory, recursive):
	for file in get_files(directory, recursive):
			print(file)
	response = input('Do you wish to proceed (Y/N)?').strip().lower()
	return response == 'y'
	
	

# Processing	
	
def process_file(file):
	slash_pos = file.rfind('\\')
	hyphen_pos = file.find('-')
	dot_pos = file.rfind('.')
	if hyphen_pos is not -1:
		artist = get_artist(file, slash_pos, hyphen_pos)
		title = get_title(file, hyphen_pos, dot_pos)
		set_metadata(file, artist, title)
	
def get_artist(file, slash_pos, hyphen_pos):
	start = slash_pos + 1 if slash_pos is not -1 else 0
	end = hyphen_pos
	return file[start:end].strip()
	
def get_title(file, hyphen_pos, dot_pos):
	start = hyphen_pos + 1
	end = dot_pos if dot_pos is not -1 else len(file)
	return file[start:end].strip()
	
	
def set_metadata(file, artist, title):
	try:
		audio = eyed3.load(file)
		audio.tag.artist = artist
		audio.tag.album = artist
		audio.tag.album_artist = artist
		audio.tag.title = title
		audio.tag.track_num = 0
		audio.tag.save()
		print('File "{}" set to artist: "{}", title: "{}"\n'.format(file, artist, title))
	except IOError:
		print("IOError with file {}".format(file))
	
	
	
	
# Main
	
def main():
	directory = fetch_directory()
	recursive = fetch_recursive()
	files = get_files(directory, recursive)
	if fetch_proceed(directory, recursive):
		for file in files:
			process_file(file)
		
if __name__ == '__main__':
	main()
