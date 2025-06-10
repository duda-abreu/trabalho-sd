import sys
from src.peer.peer_node import PeerNode
import time

peer_id = sys.argv[1] if len(sys.argv) > 1 else f"peer_default"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001
tracker_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5000"

peer = PeerNode(peer_id, tracker_url, port)
peer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    peer.shutdown()
