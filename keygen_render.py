#!/usr/bin/env python3
"""
Spaceship — Non-interactive keygen for CI/CD environments.

Reads SPACESHIP_ACCESS_KEY from environment, hashes it, and writes
the result to instance/access.key.  Used during Render build steps
where interactive input is not possible.
"""

import hashlib
import os
import secrets

key = os.environ.get("SPACESHIP_ACCESS_KEY", "")
if not key:
    print("SPACESHIP_ACCESS_KEY not set — skipping keygen.")
    exit(0)

os.makedirs("instance", exist_ok=True)
salt = secrets.token_hex(16)
digest = hashlib.sha256((salt + key).encode("utf-8")).hexdigest()

key_path = os.path.join("instance", "access.key")
with open(key_path, "w") as f:
    f.write(f"{salt}:{digest}\n")

os.chmod(key_path, 0o600)
print("Access key hash generated for production.")
