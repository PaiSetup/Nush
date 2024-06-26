import hashlib
import mimetypes
import os


def get_file_hash(file_path):
    try:
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        return None
    bytes_left = min(128 * 1024, file_size)
    chunk_size = 8096

    hash_function = hashlib.new("blake2b")
    with open(file_path, "rb") as file:
        while bytes_left != 0:
            current_chunk_size = min(chunk_size, bytes_left)
            chunk = file.read(current_chunk_size)
            hash_function.update(chunk)
            bytes_left -= current_chunk_size
    return hash_function.hexdigest()[0:48]


def get_file_mime_type(file_path):
    return mimetypes.guess_type(file_path)[0]
