# TCP server written using coroutines

This is a simple TCP server which:

(1) listens for connections on single TCP port
(2) interprets each non-empty line sent by a client as an URL
(3) performs HTTP GET request at this URL
(4) sends back to a client a single line containing MD5 hash of 
    the HTTP response
(5) caches the responses (MD5 hashes) for 60 seconds
(6) disconnects in case of any error

server-st.py
    single-threaded (synchronous) implementation, handles at most one
    client connection at a time

server-select.py
    select-based multiplexed (asynchronous) implementation, handles
    multiple connections at a time


<=== DOWNSTREAM                  UPSTREAM ===>
     (DOWN)                      (UP)

<= clients     [this program]       servers =>
(line-oriented                          (HTTP)
 multi-line
 telnet protocol)

-----> 
    receive request from downstream client
    parse request
    send request to upstream server
    ------>
    <------
    receive response from upstream server 
    generate downstream response (MD5 hash) based on upstream response
    send response to downstream client
<-----

