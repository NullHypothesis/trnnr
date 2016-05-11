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
import logging as log

# pip3 install python-Levenshtein

import Levenshtein

# pip3 install stem

from stem.descriptor.remote import DescriptorDownloader

log.basicConfig(level=log.getLevelName("INFO"),
                format="%(asctime)s [%(levelname)s]: %(message)s")


def to_str(desc):
    """
    Turn relay descriptor into string.
    """

    dir_port = desc.dir_port
    if dir_port is None:
        dir_port = 0

    return "%s%s%d%d%s%s%d%d%d%s%s%d%s" % (desc.nickname,
                                           desc.address,
                                           desc.or_port,
                                           dir_port,
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

    return parser.parse_args()


def print_desc(desc):
    """
    Print a descriptor.
    """

    print("%s,%s,%s,%d,%s,%s,%d,%s" %
          (desc.fingerprint,
           desc.nickname,
           desc.address,
           desc.or_port,
           desc.tor_version,
           desc.operating_system,
           desc.observed_bandwidth,
           desc.contact))


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


def process_descriptors(relay_fpr, num_results):
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

    print("distance,fingerprint,nickname,addr,orport,version,os,bw,contact")
    for i, elem in enumerate(sorted_dists):
        if i == num_results:
            break
        fingerprint, distance = elem
        print("%3d," % distance, end="")
        print_desc(descs[fingerprint])

    return 0


if __name__ == "__main__":

    args = parse_args()
    try:
        sys.exit(process_descriptors(args.relay, args.top))
    except KeyboardInterrupt:
        pass
