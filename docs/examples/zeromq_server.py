import zmq

from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")


if __name__ == "__main__":
    socket = zmq.Context().socket(zmq.REP)
    # A bigger message disconnects the client. The default is no limit.
    socket.setsockopt(zmq.MAXMSGSIZE, 1_000_000)
    socket.bind("tcp://127.0.0.1:8000")
    while True:
        request = socket.recv_string()
        # A REP socket must reply to every request, so a notification gets an
        # empty message. max_batch_size: see the Security page.
        socket.send_string(dispatch(request, max_batch_size=100))
