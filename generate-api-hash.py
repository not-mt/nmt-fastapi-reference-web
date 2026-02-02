#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Generate Argon2 hashes for API key configuration.

This script provides secure generation of Argon2 password hashes suitable for storing
API keys in configuration files. It includes verification of matching input and
empty input validation.

Example:
    $ python generate_api_hash.py
    Create a new API key hash:
    Enter API key:
    Confirm API key:

    Generated Argon2 hash:
    $argon2id$v=19$m=65536,t=3,p=4$B1c3Qx3S...SDfjsjfg
"""

from getpass import getpass

from argon2 import PasswordHasher


def generate_hash() -> None:
    """Generate and print an Argon2 hash from user-provided API key.

    Prompts for the API key twice for verification, validates non-empty input,
    then generates and displays the Argon2 hash.
    """
    print("Create a new API key hash:")
    while True:
        key1: str = getpass("Enter API key: ")
        key2: str = getpass("Confirm API key: ")

        if key1 != key2:
            print("Error: Keys don't match. Please try again.")
            continue

        if not key1:
            print("Error: Key cannot be empty.")
            continue

        ph: PasswordHasher = PasswordHasher()
        api_hash: str = ph.hash(key1)
        print("\nGenerated Argon2 hash:")
        print(f"\n{api_hash}\n")
        break


if __name__ == "__main__":
    generate_hash()
