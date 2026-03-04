#!/usr/bin/env python3
"""
Spaceship — Key Manager

Generates a SHA-256 salted hash of your chosen access key and writes it
to instance/access.key.  The plaintext key is never stored anywhere.

Usage:
    python keygen.py

You will be prompted to type your key (hidden input).
Run this again at any time to change the key.
"""

import getpass
import hashlib
import os
import secrets
import sys


INSTANCE_DIR = os.path.join(os.path.dirname(__file__), "instance")
KEY_FILE = os.path.join(INSTANCE_DIR, "access.key")


def hash_key(plaintext: str, salt: str) -> str:
    """Produce a hex digest from salt + plaintext using SHA-256."""
    return hashlib.sha256((salt + plaintext).encode("utf-8")).hexdigest()


def main():
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    print("╔══════════════════════════════════════╗")
    print("║   Spaceship — Ground Station Keygen  ║")
    print("╚══════════════════════════════════════╝")
    print()

    key = getpass.getpass("Enter your new access key: ")
    if len(key) < 6:
        print("Key must be at least 6 characters.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm key: ")
    if key != confirm:
        print("Keys do not match.")
        sys.exit(1)

    salt = secrets.token_hex(16)
    digest = hash_key(key, salt)

    with open(KEY_FILE, "w") as f:
        # Format:  salt:hash
        f.write(f"{salt}:{digest}\n")

    os.chmod(KEY_FILE, 0o600)  # owner-read-write only

    print()
    print(f"Key hash written to {KEY_FILE}")
    print("Keep this file safe. Re-run this script to change your key.")


if __name__ == "__main__":
    main()
