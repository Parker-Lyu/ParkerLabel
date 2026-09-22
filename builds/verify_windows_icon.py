import argparse
import hashlib
import struct
from collections import Counter
from pathlib import Path


def icon_payloads(path):
    data = Path(path).read_bytes()
    if len(data) < 6:
        raise ValueError("Invalid ICO header")
    reserved, image_type, count = struct.unpack_from("<HHH", data)
    if reserved or image_type != 1 or not count or len(data) < 6 + count * 16:
        raise ValueError("Invalid ICO directory")
    payloads = []
    for index in range(count):
        size, offset = struct.unpack_from("<II", data, 14 + index * 16)
        if not size or offset + size > len(data):
            raise ValueError("Invalid ICO image entry")
        payloads.append(data[offset : offset + size])
    return payloads


def executable_icon_payloads(path):
    import pefile

    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
        )
        payloads = []
        for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if resource_type.id != pefile.RESOURCE_TYPE["RT_ICON"]:
                continue
            for resource_id in resource_type.directory.entries:
                for language in resource_id.directory.entries:
                    entry = language.data.struct
                    payloads.append(pe.get_data(entry.OffsetToData, entry.Size))
        return payloads
    finally:
        pe.close()


def payload_hashes(payloads):
    return Counter(hashlib.sha256(payload).digest() for payload in payloads)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--icon", type=Path, required=True)
    args = parser.parse_args()
    expected = payload_hashes(icon_payloads(args.icon))
    actual = payload_hashes(executable_icon_payloads(args.executable))
    if actual != expected:
        raise SystemExit("Executable icon resources do not match the project icon")


if __name__ == "__main__":
    main()
