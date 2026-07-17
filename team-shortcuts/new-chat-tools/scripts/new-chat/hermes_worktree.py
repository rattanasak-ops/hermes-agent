#!/usr/bin/env python3
"""Portable entry point for the Hermes Worktree Lifecycle Manager."""

from __future__ import annotations

import argparse
import sys

from hermes_cli.worktree_lifecycle import register_worktree_subparser


def main() -> None:
    parser = argparse.ArgumentParser(prog="hermes-worktree")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_worktree_subparser(subparsers)
    args = parser.parse_args(["worktree", *sys.argv[1:]])
    args.func(args)


if __name__ == "__main__":
    main()
