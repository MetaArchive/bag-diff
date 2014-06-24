bag-diff
========

## Note
This script has only been developed and tested using bagit-python v1.2.1.
If things aren't working correctly, try grabbing that version of bagit-python
and placing it in the same directory as this script (or installing it).

## Overview
This tool will generate what we call a "Bag Diff"; A new Change Bag encapsulating any modified or added files is the result. This Change Bag can be ingested into a repository alongside the previously ingested Bag to which the Change Bag might relate. This helps to avoid data duplication. A list of all added, modified, and deleted files is printed to the screen. Currently this information must be noted outside of the bag for referencing any deleted files at a later date for the purposes of cleanup. The script could be enhanced to include this information in the bag-info.txt file of the resulting Change Bag.

## Usage
   
   Usage:
        % python bag-diff.py -m /path/to/old/manifests/dir /path/to/bag

The Change Bag will be created as /path/to/bag_changes0, or you can specify
the path yourself using the -o argument.

## License

See LICENSE.txt

