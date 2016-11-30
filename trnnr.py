#!/usr/bin/env python3
#
# Copyright 2016 Philipp Winter <phw@nymity.ch>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Implements Tor relay nearest neighbour search.

Given a reference Tor relay, the idea is to find other Tor relays whose
configuration is very similar to the reference relay.  That includes relays
that share a nickname, port, operating system, or bandwidth values.

To use this tool, you only need the fingerprint of a Tor relay whose nearest
neighbours you want to find, e.g., 9695DFC35FFEB861329B9F1AB04C46397020CE31.
Then, run the tool as follows:

    ./trnns.py 9695DFC35FFEB861329B9F1AB04C46397020CE31

The output is a list of CSV-formatted relays, one per line.  The first column
shows the Levenshtein distance.  The smaller the number, the more similar the
relay's configuration is to the reference relay.
"""

import sys
import time
import argparse
import operator
import itertools
import logging as log

# pip3 install python-Levenshtein stem tabulate termcolor

import Levenshtein
import tabulate
import termcolor
from stem.descriptor.remote import DescriptorDownloader


log.basicConfig(level=log.getLevelName("INFO"),
                format="%(asctime)s [%(levelname)s]: %(message)s")


def dirport_to_int(dir_port):
    """
    If the dirport is `None', return 0.
    """

    if dir_port is None:
        return 0
    else:
        return dir_port


def to_str(desc):
    """
    Turn relay descriptor into string.
    """

    return "%s%s%d%d%s%s%d%d%d%s%s%d%s" % (desc.nickname,
                                           desc.address,
                                           desc.or_port,
                                           dirport_to_int(desc.dir_port),
                                           desc.tor_version,
                                           desc.exit_policy,
                                           desc.average_bandwidth,
                                           desc.burst_bandwidth,
                                           desc.observed_bandwidth,
                                           desc.operating_system,
                                           desc.published,
                                           desc.uptime,
                                           desc.contact)


def parse_args():
    """
    Parse and return command line arguments.
    """

    desc = "Find nearest neighbours of given relay."
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("relay",
                        metavar="RELAY",
                        type=str,
                        help="Fingerprint of relay whose nearest neighbours "
                             "we will find.")

    parser.add_argument("-t",
                        "--top",
                        type=int,
                        default=20,
                        help="The number of most similar relays to display "
                             "(default=20).")

    parser.add_argument("-c",
                        "--colour",
                        action="store_true",
                        default=False,
                        help="Use terminal colours to visually highlight the "
                             "difference between relays (default=false).")

    return parser.parse_args()


def desc_to_str(desc):
    """
    Return a string representation of the given descriptor.
    """

    return "%s,%s,%s,%d,%d,%s,%s,%d,%d,%d,%d,%s" % \
           (desc.fingerprint[:8],
            desc.nickname,
            desc.address,
            desc.or_port,
            dirport_to_int(desc.dir_port),
            desc.tor_version,
            desc.operating_system,
            desc.average_bandwidth,
            desc.burst_bandwidth,
            desc.observed_bandwidth,
            desc.uptime,
            desc.contact)


def format_desc(desc, ref_desc, use_colour):
    """
    Return potentially colourised string list of descriptor features.
    """

    desc, ref_desc = desc_to_str(desc), desc_to_str(ref_desc)
    final_string = ""

    for string, ref_string in zip(desc.split(","), ref_desc.split(",")):
        for char, ref_char in itertools.zip_longest(string, ref_string):

            # If a character in the string is identical to the reference
            # string, we highlight it in red.  That makes it easier to visually
            # spot similarities in the descriptors.

            if (char == ref_char) and use_colour:
                final_string += termcolor.colored(char, "red")
            else:
                final_string += char if char is not None else " "

        final_string += ","

    return final_string.split(",")


def fetch_descriptors():
    """
    Fetch and return relay descriptors.
    """

    downloader = DescriptorDownloader(use_mirrors=True, timeout=20)
    query = downloader.get_server_descriptors(validate=False)

    descs = {}
    try:
        for desc in query.run():
            descs[desc.fingerprint] = desc
        log.info("Query took %0.2f seconds." % query.runtime)
    except Exception as exc:
        log.critical("Unable to retrieve server descriptors: %s" % exc)

    log.info("Downloaded %d descs." % len(descs))

    return descs


def process_descriptors(relay_fpr, num_results, use_colour):
    """
    Run linear nearest-neighbour search over all descriptors we can get.
    """

    descs = fetch_descriptors()
    reference = descs.get(relay_fpr, None)
    if reference is None:
        log.critical("Reference relay not found in descriptors.")
        return 1
    reference_str = to_str(reference)

    # Determine Levenshtein distance between reference relay and all other
    # relays that we could fetch.

    dists = dict()
    before = time.time()

    for i, (fingerprint, desc) in enumerate(descs.items()):
        dists[desc.fingerprint] = Levenshtein.distance(reference_str,
                                                       to_str(desc))
        if (i % 1000) == 0:
            log.info("Processed %d descriptors." % i)

    sorted_dists = sorted(dists.items(), key=operator.itemgetter(1))
    log.info("Processing time: %.3f" % (time.time() - before))

    # Display the top n results.

    lines = [["distance", "fingerprint", "nickname", "addr", "orport",
              "dirport", "version", "os", "avgbw", "burstbw", "obsbw",
              "uptime", "contact"]]
    for i, elem in enumerate(sorted_dists):
        if i == num_results:
            break
        fingerprint, distance = elem
        line = format_desc(descs[fingerprint], descs[relay_fpr], use_colour)
        lines.append(["%3d" % distance] + line)

    # Finally, nicely print all results in tabular form.

    print(tabulate.tabulate(lines))

    return 0


if __name__ == "__main__":

    args = parse_args()
    try:
        sys.exit(process_descriptors(args.relay, args.top, args.colour))
    except KeyboardInterrupt:
        pass
