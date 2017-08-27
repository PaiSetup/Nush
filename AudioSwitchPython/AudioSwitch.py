from typing import List, Tuple
import os


class IllegalState(Exception):
    def __init__(self, message):
        self.message = message


class AudioSwitch:
    NIRCMD = "nircmd.exe"
    FILE = 'config.txt'
    MESSAGE_NO_DEVICES = "At least one device should be specified in {}".format(FILE)
    MESSAGE_NO_FILE = "Create file named {} containing names of devices you want to swap over".format(FILE)
    MESSAGE_NO_NIRCMD = "Place nircmd.exe in the same directory with the script or include it in PATH variable".format(FILE)

    def __init__(self):
        try:
            self._check_dependencies()
            self._current_device, self._devices = self._read_devices()
            self._legal = True
        except IllegalState as illegal_state:
            print(illegal_state.message)
            self._legal = False

    @staticmethod
    def _check_dependencies():
        if os.system('where {}'.format(AudioSwitch.NIRCMD)) != 0:
                raise IllegalState(AudioSwitch.MESSAGE_NO_NIRCMD)

    @staticmethod
    def _read_devices() -> Tuple[int, List[str]]:
        """IO Function
        
        Reads current device from first line and devices list from remaining lines
        Defaults current device to 0 if not supplied
        """
        try:
            with open(AudioSwitch.FILE, 'r') as file:
                lines = file.read().split(sep='\n')
                try:
                    current = int(lines[0])
                    devices = lines[1:]
                except ValueError:
                    current = 0
                    devices = lines
                AudioSwitch._clear_list(devices)
                if len(devices) == 0:
                    raise IllegalState(AudioSwitch.MESSAGE_NO_DEVICES)
                return current, devices
        except OSError:
            raise IllegalState(AudioSwitch.MESSAGE_NO_FILE)

    @staticmethod
    def _clear_list(arg):
        for i in range(len(arg)-1, -1, -1):
            if arg[i].strip() == '':
                del arg[i]

    def _set_device(self, index):
        self._current_device = index
        device = self._devices[self._current_device]
        os.system('{0} setdefaultsounddevice "{1}" 0'
                  '{0} setdefaultsounddevice "{1}" 1'
                  '{0} setdefaultsounddevice "{1}" 2'.format(AudioSwitch.NIRCMD, device))

        try:
            with open(AudioSwitch.FILE, 'w') as file:
                lines = '\n'.join([self._current_device.__str__()] + self._devices)
                file.writelines(lines)
        except OSError:
            pass  # Cannot do anything, index just won't be updated



    def device_next(self, rotate=True):
        if not self._legal:
            return

        index = self._current_device + 1
        self.device_at_index(index, rotate)

    def device_previous(self, rotate=True):
        if not self._legal:
            return

        index = self._current_device - 1
        self.device_at_index(index, rotate)

    def device_at_index(self, index, rotate_index=True):
        if not self._legal:
            return

        clamp = lambda min_value, x, max_value: max(min(x, max_value), min_value)
        rotate = lambda min_value, x, max_value: (x - min_value) % (max_value - min_value + 1) + min_value
        index_function = rotate if rotate_index else clamp

        index = index_function(0, index, len(self._devices) - 1)
        self._set_device(index)
