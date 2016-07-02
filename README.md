# trnnr

This tool implements Tor relay nearest neighbour ranking.  Given a reference Tor
relay, the idea is to rank other Tor relays based on whose configuration is very
similar to the reference relay.  That includes relays that share a nickname,
port, operating system, or bandwidth values.

To use this tool, you only need the fingerprint of a Tor relay whose nearest
neighbours you want to see, e.g., `9B94CD0B7B8057EAF21BA7F023B7A1C8CA9CE645`.
Then, run the tool as follows:

    ./trnnr.py 9B94CD0B7B8057EAF21BA7F023B7A1C8CA9CE645

The output is a list of CSV-formatted relays, one per line.  The first column
shows the Levenshtein distance.  The smaller the number, the more similar the
relay's configuration is to the reference relay.

To see the 10 most similar relays, run:

    ./trnnr.py 9B94CD0B7B8057EAF21BA7F023B7A1C8CA9CE645 --top 10

Finally, to further visually highlight similarities in the output, run:

    ./trnnr.py 9B94CD0B7B8057EAF21BA7F023B7A1C8CA9CE645 --top 10 --colour

This will result in output similar to the following image.

![trnnr screenshot](https://nullhypothesis.github.com/trnnr-screenshot.png)
