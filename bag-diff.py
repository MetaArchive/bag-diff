#!/usr/bin/env python
"""
BagIt "Bag Diff" Generator
by Stephen Eisenhauer
last updated 2013-07-05

Note: This script has only been developed and tested using bagit-python v1.2.1.
If things aren't working correctly, try grabbing that version of bagit-python
and placing it in the same directory as this script (or installing it).

This tool will generate what we call a "Bag Diff"; A new Change Bag encapsulating any modified or added files is the result. This Change Bag can be ingested into a repository alongside the previously ingested Bag to which the Change Bag might relate. This helps to avoid data duplication. A list of all added, modified, and deleted files is printed to the screen. Currently this information must be noted outside of the bag for referencing any deleted files at a later date for the purposes of cleanup. The script could be enhanced to include this information in the bag-info.txt file of the resulting Change Bag.
   
   Usage:
        % python bag-diff.py -m /path/to/old/manifests/dir /path/to/bag

The Change Bag will be created as /path/to/bag_changes0, or you can specify
the path yourself using the -o argument.
"""
import os
import sys
import shutil
import argparse
import bagit
import re


# Exit status codes
class Status:
    SUCCESS = 0
    NO_CHANGES = 1


def read_checksums(manifest_path):
    """
    An iterator that provides (path, hash) tuples from a BagIt manifest
    (or tagmanifest) file.
    """
    manifest_file = open(manifest_path, 'rb')

    try:
        for line in manifest_file:
            line = line.strip()

            # Ignore blank lines and comments.
            if line == "" or line.startswith("#"): continue

            entry = line.split(None, 1)

            # Ignore lines not containing exactly 2 tokens
            if len(entry) != 2: continue

            entry_hash = entry[0]
            entry_path = os.path.normpath(entry[1].lstrip("*"))
            
            yield (entry_path, entry_hash)
    finally:
        manifest_file.close()


def load_manifests(manifests_dir):
    """
    Finds all [tag]manifest-*.txt files in manifests_dir and loads their
    entries into a easy-to-navigate dict.
    """
    checksums = {
        'payload': {},
        'tags': {}
    }
    
    for f in os.listdir(manifests_dir):
        match = re.match("^([a-z]+)-([a-z0-9]+)\.txt$", f)
        f_abs = os.path.abspath(os.path.join(manifests_dir, f))
        if os.path.isfile(f_abs) and match:
            manifest_type = None
            if match.group(1) == "manifest":
                manifest_type = "payload"
            elif match.group(1) == "tagmanifest":
                manifest_type = "tags"
            if manifest_type:
                algo = match.group(2)
                checksums[manifest_type][algo] = {}
                for entry in read_checksums(f_abs):
                    checksums[manifest_type][algo][entry[0]] = entry[1]
    return checksums


def make_bag_diff_from_manifests(bag_path, manifests_path, output_path, skip_verify=False):
    """
    Diff a bag against a previous version of its own manifest(s). These
    old manifest files should be placed in a directory whose path is
    given as manifests_path.
    
    """
    # Load Manifests dir's manifest(s) into a data structure
    manifests_checksums = load_manifests(manifests_path)
    
    if len(manifests_checksums['tags']) == 0:
        print "WARNING: No tagmanifest files found in manifests directory. Tag files cannot be included in this diff."
    
    # Load Bag's manifests into a data structure
    bag_checksums = load_manifests(bag_path)
    
    # Prune any sections from each structure that don't exist in the other
    for m_type in manifests_checksums:
        for algo in manifests_checksums[m_type]:
            if not algo in bag_checksums[m_type]:
                del manifests_checksums[m_type][algo]
    for m_type in bag_checksums:
        for algo in bag_checksums[m_type]:
            if not algo in manifests_checksums[m_type]:
                del bag_checksums[m_type][algo]
    
    # At this point, the two structures should be "balanced" enough for 
    # easy comparison (neither one contains entries from a kind of
    # manifest that the other one lacks)
    
    # Iterate and compare checksums to find modifications/deletions
    added = set()
    deleted = set()
    modified = set()
    for m_type in manifests_checksums:
        for algo in manifests_checksums[m_type]:
            for path in manifests_checksums[m_type][algo]:
                if not path in bag_checksums[m_type][algo]:
                    deleted.add(path) # Path is in old manifests but not in current bag
                elif manifests_checksums[m_type][algo][path] != bag_checksums[m_type][algo][path]:
                    modified.add(path) # Checksum has changed for path
    
    # Now compare in reverse to find additions
    for m_type in bag_checksums:
        for algo in bag_checksums[m_type]:
            for path in bag_checksums[m_type][algo]:
                if not path in manifests_checksums[m_type][algo]:
                    added.add(path) # Path is in bag but not in old manifests
    
    print "Added:"
    print added
    print "Deleted:"
    print deleted
    print "Modified:"
    print modified
    
    # If all of these lists are empty, abort
    if (len(modified) + len(added) + len(deleted)) == 0:
        print "Nothing to do; No changes were detected."
        return Status.NO_CHANGES
    
    # Create directory for the bag diff
    os.makedirs(output_path)
    
    # Copy the manifests themselves into the bag diff for safekeeping
    for f in os.listdir(bag_path):
        if os.path.isfile(os.path.join(bag_path, f)) and \
        re.match("^(tag)?manifest-([a-z0-9]+)\.txt$", f):
            shutil.copy2(os.path.join(bag_path, f), output_path)

    # Load output directory with modified and added files
    added_and_modified = added.union(modified)
    for path in added_and_modified:
        dest = os.path.join(output_path, os.path.dirname(path))
        if not os.path.isdir(dest):
            os.makedirs(dest)
        shutil.copy2(os.path.join(bag_path, path), dest)
    
    # Prepare metadata for new Bag Diff
    # This should likely inherit contact info and identifier info from the 
    # parent bag, and include a change digest in the long description
    baginfo = {
        'Contact-Name': 'Who knows?'
    }
    
    # Bag-ify the Bag Diff
    bagit.make_bag(output_path, baginfo)

    return Status.SUCCESS


def _make_arg_parser():
    parser = argparse.ArgumentParser(
        description='Tools for generating BagIt Change Bags.')
    parser.add_argument('bag',
        help="path to the bag")
    parser.add_argument('--no-verify', action="store_true",
        help="skips checksum validation (not recommended)")
    parser.add_argument('-o', '--output-dir',
        help="directory name to use for the output bag. "
        "(relative to working directory)"
    )
    parser.add_argument('-m', '--old-manifest-dir',
        help="path to a directory containing older manifests for this bag "
        "(to use as a reference point for the diff)"
    )

    return parser


if __name__ == "__main__":
    # Arguments
    parser = _make_arg_parser()
    args = parser.parse_args()
    bag_path = os.path.abspath(args.bag)
    manifests_path = args.old_manifest_dir
    
    # Determine the diff output directory to use
    output_path = args.output_dir
    if not output_path:
        change_num = 0
        while True:
            output_path = "%s_changes%d" % (bag_path, change_num)
            if os.path.isdir(output_path):  # if dir already exists
                change_num += 1             # try next number
            else:
                break
    print "Using output path: " + output_path

    # Call the appropriate operation
    if manifests_path:
        manifests_path = os.path.abspath(manifests_path)
        status = make_bag_diff_from_manifests(bag_path, manifests_path,
                                              output_path, args.no_verify)
    else:
        status = make_bag_diff(bag_path, output_path, args.no_verify)
    
    sys.exit(status)
