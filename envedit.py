import os
import time

# Exception

class QuitError(Exception):
	pass

# Helpers

def load_environment(name):
	return os.environ[name].split(sep=';')

def load_file(file_path):
	with open(file_path, mode='r') as file:
		content = file.read().strip()
	return content.split(sep=';')

def save(header, variable, file_path):
	with open(file_path, mode='a') as file:
		if header is not None and header != "":
			timestamp = time.strftime("%c")
			file.write("{} ({})\n".format(header, timestamp))
		file.write("{}\n".format(';'.join(variable)))

def print_variable(variable):
	if len(variable) > 0:
		for i, v in enumerate(variable):
			print('{}: "{}"'.format(i, v))
		print()
	
	
	
# Actions

def action_add(variable, choice_tokens):
	value = choice_tokens[1]
	variable.append(value)

def action_delete(variable, choice_tokens):
	to_delete = [int(x) for x in choice_tokens[1:]]
	for index in range(len(variable)-1, -1, -1):
		if index in to_delete:
			del(variable[index])

def action_filter(variable, choice_tokens):
	filter = [int(x) for x in choice_tokens[1:]]
	print(filter)
	for index in range(len(variable)-1, -1, -1):
		if index not in filter:
			del(variable[index])

def action_load_environment(variable, choice_tokens):
	name = choice_tokens[1]
	loaded = load_environment(name)
	
	del(variable[:])
	variable.extend(loaded)

def action_load_file(variable, choice_tokens):
	file_path = choice_tokens[1]
	loaded = load_file(file_path)

	del(variable[:])
	variable.extend(loaded)


def action_save(variable, choice_tokens):
	file_path = choice_tokens[1]
	header = choice_tokens[2] if len(choice_tokens) > 2 else None
	save(header, variable, file_path)

def action_backup(variable, choice_tokens):
	name = choice_tokens[1]
	file_path = choice_tokens[2]
	header = choice_tokens[3] if len(choice_tokens) > 3 else None

	save(header, load_environment(name), file_path)


def action_quit(variable, choice_tokens):
	raise QuitError


actions = [
	action_add, action_delete, action_filter, action_load_environment, 
	action_load_file, action_save, action_backup, action_quit
]




# Main screen

def screen_main():
	variable = []
	while True:
		os.system("cls")
		print_variable(variable)
		
		print('Perform selected action')
		print('  1.Add item:\t\t"1 value"')
		print('  2.Delete\t\t"2 index1 index2 ..."')
		print('  3.Filter\t\t"3 index1 index2 ..."')
		print('  4.LoadEnvironment\t"4 var_name"')
		print('  5.LoadFile\t\t"5 file_path"')
		print('  6.Save\t\t"6 file_path header(optional)"')
		print('  7.Backup\t\t"7 var_name file_path header(optional)"')
		print('  8.Quit\t\t"8"')

		try:
			choice = input('Choice: ').strip()
			choice_tokens = choice.split()
			action_index = int(choice_tokens[0]) - 1

			action = actions[action_index]
			action(variable, choice_tokens)
		except (EOFError, QuitError):
			break
		except (ValueError, IndexError, FileNotFoundError):
			continue




# script
	
if __name__ == '__main__':
	screen_main()