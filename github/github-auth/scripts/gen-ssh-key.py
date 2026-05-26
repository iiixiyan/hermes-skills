#!/usr/bin/env python3
"""
Generate an Ed25519 SSH key pair using Python's cryptography library.

Fallback when `ssh-keygen` is not available or broken (e.g., OpenSSL version
mismatch between the linked and runtime libraries).

Usage:
    python3 gen-ssh-key.py [--comment "user@host"] [--keyfile ~/.ssh/id_ed25519]

Output:
    ~/.ssh/id_ed25519          (private key, chmod 600)
    ~/.ssh/id_ed25519.pub      (public key with comment)
"""

import argparse
import os
import stat
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def gen_ssh_key(comment: str, keyfile: str) -> None:
    """Generate Ed25519 key pair and write to disk."""

    # Create parent directory
    keydir = os.path.dirname(os.path.abspath(keyfile))
    os.makedirs(keydir, exist_ok=True)

    # Generate key
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize private key in OpenSSH PEM format (no passphrase)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key in OpenSSH one-line format
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    # Write private key
    priv_path = keyfile
    with open(priv_path, "wb") as f:
        f.write(private_bytes)
    os.chmod(priv_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    # Write public key
    pub_path = keyfile + ".pub"
    pub_line = public_bytes.decode().strip() + " " + comment + "\n"
    with open(pub_path, "w") as f:
        f.write(pub_line)

    print(f"✅ Private key: {priv_path}")
    print(f"✅ Public key:  {pub_path}")
    print(f"\n🔑 Public key for GitHub:\n{pub_line.strip()}")

    # Verify the keys are readable
    with open(priv_path) as f:
        assert f.read().startswith("-----BEGIN OPENSSH PRIVATE KEY-----"), "Bad private key format"
    with open(pub_path) as f:
        assert f.read().startswith("ssh-ed25519"), "Bad public key format"

    print("\n✅ Keys verified. Add the public key to: https://github.com/settings/keys")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Ed25519 SSH key pair via Python cryptography")
    parser.add_argument(
        "--comment",
        default="hermes-agent@host",
        help="Comment appended to the public key (default: hermes-agent@host)",
    )
    parser.add_argument(
        "--keyfile",
        default=os.path.expanduser("~/.ssh/id_ed25519"),
        help="Path for the private key file (default: ~/.ssh/id_ed25519)",
    )
    args = parser.parse_args()

    # Check that cryptography is available
    try:
        gen_ssh_key(args.comment, args.keyfile)
    except ImportError as e:
        print(f"❌ Required library not found: {e}")
        print("   Install with: pip install cryptography")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to generate key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
