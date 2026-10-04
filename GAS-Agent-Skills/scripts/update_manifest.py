#!/usr/bin/env python3
"""Check the package SHA-256 manifest; only --write changes it (Python 3.9+)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


MANIFEST = "manifest.sha256.json"


def configure_output():
    """Keep the host encoding, escaping only characters that it cannot display."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def checked_path(path, missing_leaf=False):
    """Reject links/reparse points in the lexical path, including its ancestors."""
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if missing_leaf and part == path:
                return path
            raise
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Refusing symlink/reparse point: " + str(part))
    return path


def read_regular(path):
    path = checked_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Expected a regular file: " + str(path))
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(str(path), flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("File changed while opening: " + str(path))
        data = stream.read()
        after = os.fstat(stream.fileno())
    final = checked_path(path).lstat()
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size,
                              info.st_mtime_ns, info.st_ctime_ns)
    # Windows Python versions can expose different ctime semantics through
    # lstat and fstat. Compare each API against itself, not against the other.
    stable = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if (signature(before) != signature(final) or signature(opened) != signature(after)
            or stable(before) != stable(opened)):
        raise ValueError("File changed while reading: " + str(path))
    return data


def atomic_write(path, data):
    """Replace one file; callers compute package hashes before creating the temp file."""
    path = checked_path(path, missing_leaf=True)
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Expected a regular file: " + str(path))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".gas-maintenance-", dir=str(path.parent),
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        checked_path(path, missing_leaf=True)
        os.replace(str(temporary), str(path))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def package_manifest(root):
    root = checked_path(root)
    if not root.is_dir():
        raise ValueError("Package root must be a directory: " + str(root))
    files = {}

    def visit(folder):
        with os.scandir(str(checked_path(folder))) as entries:
            paths = sorted((Path(entry.path) for entry in entries), key=lambda p: p.name)
        for path in paths:
            info = checked_path(path).lstat()
            if path.name == "__pycache__":
                continue
            if stat.S_ISDIR(info.st_mode):
                visit(path)
            elif stat.S_ISREG(info.st_mode):
                # Match verify_bundle.py: exclude this basename at every depth.
                if path.name != MANIFEST:
                    files[path.relative_to(root).as_posix()] = hashlib.sha256(read_regular(path)).hexdigest()
            else:
                raise ValueError("Unsupported package entry: " + str(path))

    visit(root)
    return {"version": 1, "algorithm": "sha256", "files": dict(sorted(files.items()))}


def load_manifest(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate manifest key: " + key)
            result[key] = value
        return result

    return json.loads(read_regular(path).decode("utf-8"), object_pairs_hook=unique_pairs)


def main(argv=None):
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1],
                        help="Package directory (default: this script's parent package).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check without writing (default).")
    mode.add_argument("--write", action="store_true", help="Replace the manifest after reviewing source diffs.")
    args = parser.parse_args(argv)
    try:
        root = checked_path(args.root)
        target = checked_path(root / MANIFEST, missing_leaf=True)
        expected = package_manifest(root)
        current = None
        if target.exists():
            try:
                current = load_manifest(target)
            except (ValueError, UnicodeError) as exc:
                print("Invalid existing manifest: " + str(exc), file=sys.stderr)
        if current == expected:
            print("Manifest is current ({} files).".format(len(expected["files"])))
            return 0
        old = current.get("files", {}) if isinstance(current, dict) else {}
        if not isinstance(old, dict):
            old = {}
        new = expected["files"]
        for label, names in (("added", set(new) - set(old)), ("removed", set(old) - set(new)),
                             ("changed", {name for name in set(old) & set(new) if old[name] != new[name]})):
            for name in sorted(names):
                print(label + ": " + name)
        if not args.write:
            print("Manifest differs. Review source diffs before running --write.", file=sys.stderr)
            return 1
        # Snapshot first, then create the atomic-write temporary file: it is never self-indexed.
        atomic_write(target, (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print("Updated " + str(target))
        return 0
    except (OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
