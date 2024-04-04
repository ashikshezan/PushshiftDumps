# this is an example of loading and iterating over a single file

import json
import os
import sys
from datetime import datetime, timezone

import zstandard
from loguru import logger


def read_and_decode(reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0):
    chunk = reader.read(chunk_size)
    bytes_read += chunk_size
    if previous_chunk is not None:
        chunk = previous_chunk + chunk
    try:
        return chunk.decode()
    except UnicodeDecodeError:
        if bytes_read > max_window_size:
            raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")
        logger.info(f"Decoding error with {bytes_read:,} bytes, reading another chunk")
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)


def read_lines_zst(file_name):
    with open(file_name, 'rb') as file_handle:
        buffer = ''
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)
        while True:
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)

            if not chunk:
                break
            lines = (buffer + chunk).split("\n")

            for line in lines[:-1]:
                yield line, file_handle.tell()

            buffer = lines[-1]

        reader.close()


if __name__ == "__main__":
    file_path = sys.argv[1]
    file_size = os.stat(file_path).st_size

    file_lines = 0
    file_bytes_processed = 0
    field = "subreddit"
    value = "wallstreetbets"
    bad_lines = 0

    for line, file_bytes_processed in read_lines_zst(file_path):
        try:
            obj = json.loads(line)
            temp = obj[field] == value
        except (KeyError, json.JSONDecodeError) as err:
            bad_lines += 1
        file_lines += 1
        if file_lines % 100000 == 0:
            logger.info(
                f"File line: {file_lines:} - Bad lines: {bad_lines:} : {file_bytes_processed:,}:{(file_bytes_processed / file_size) * 100:.0f}%")
        with open("output.txt", "a") as f:
            f.write(line + "\n")
        break

    logger.info(f"Complete : {file_lines:,} : {bad_lines:,}")
