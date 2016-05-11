# trnns

This tool implements Tor relay nearest neighbour search.  Given a reference Tor
relay, the idea is to find other Tor relays whose configuration is very similar
to the reference relay.  That includes relays that share a nickname, port,
operating system, or bandwidth values.

To use this tool, you only need the fingerprint of a Tor relay whose nearest
neighbours you want to find, e.g., `9695DFC35FFEB861329B9F1AB04C46397020CE31`.
Then, run the tool as follows:

    ./trnns.py 9695DFC35FFEB861329B9F1AB04C46397020CE31

The output is a list of CSV-formatted relays, one per line.  The first column
shows the Levenshtein distance.  The smaller the number, the more similar the
relay's configuration is to the reference relay.
