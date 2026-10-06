import zmq

from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")


if __name__ == "__main__":
    socket = zmq.Context().socket(zmq.REP)
    socket.bind("tcp://*:5000")
    while True:
        request = socket.recv_string()
        # A REP socket must reply to every request, so a notification gets an
        # empty message.
        socket.send_string(dispatch(request))
