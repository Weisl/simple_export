#!/usr/bin/env python3
"""Private dev builds: tag them and stamp their version into the manifest.

A dev build is tagged vX.Y.Z-dev.N, where X.Y.Z is the upcoming version in
blender_manifest.toml. Pushing such a tag runs the Test Build workflow, which
uploads the zip as a workflow artifact. It never creates a GitHub release, and
the add-on's update check (releases/latest) never sees it. A dev build sorts
before its release, so an installed 0.8.2-dev.3 reports 0.8.2 as an update.

    python .github/scripts/dev_version.py tag [REF]   create the next dev tag on REF (default HEAD)
    python .github/scripts/dev_version.py stamp TAG   write TAG's version into blender_manifest.toml

Push a created tag with: git push origin vX.Y.Z-dev.N
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / "blender_manifest.toml"
VERSION_LINE_RE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
DEV_TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)-dev\.(\d+)$")


def read_manifest_version(manifest):
    match = VERSION_LINE_RE.search(manifest.read_text(encoding="utf-8"))
    if not match:
        sys.exit(f"No version line in {manifest}")
    return match.group(1)


def next_dev_tag(version):
    tags = subprocess.run(["git", "tag", "--list", f"v{version}-dev.*"],
                          capture_output=True, text=True, check=True).stdout.split()
    numbers = [int(m.group(2)) for m in map(DEV_TAG_RE.match, tags) if m]
    return f"v{version}-dev.{max(numbers, default=0) + 1}"


def cmd_tag(args):
    version = read_manifest_version(args.manifest)
    if "-" in version:
        sys.exit(f"Manifest version {version} must be a plain X.Y.Z release version")
    tag = next_dev_tag(version)
    subprocess.run(["git", "tag", "-a", tag, args.ref, "-m", f"Dev build {tag[1:]}"], check=True)
    print(tag)


def cmd_stamp(args):
    match = DEV_TAG_RE.match(args.tag)
    if not match:
        sys.exit(f"{args.tag} is not a dev tag (vX.Y.Z-dev.N)")
    version = read_manifest_version(args.manifest)
    if match.group(1) != version:
        sys.exit(f"Tag {args.tag} does not match blender_manifest.toml version {version}")
    text = args.manifest.read_text(encoding="utf-8")
    args.manifest.write_text(VERSION_LINE_RE.sub(f'version = "{args.tag[1:]}"', text, count=1), encoding="utf-8")
    print(f"Stamped {args.manifest.name} with version {args.tag[1:]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    sub = parser.add_subparsers(dest="command", required=True)
    tag = sub.add_parser("tag", help="create the next dev tag")
    tag.add_argument("ref", nargs="?", default="HEAD")
    tag.set_defaults(func=cmd_tag)
    stamp = sub.add_parser("stamp", help="write a dev tag's version into the manifest")
    stamp.add_argument("tag")
    stamp.set_defaults(func=cmd_stamp)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
