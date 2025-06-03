import unittest
from src.peer.peer_node import PeerNode

class TestPeerNode(unittest.TestCase):
    def setUp(self):
        self.peer = PeerNode("peer1", "http://localhost:5000")

    def test_initial_state(self):
        self.assertEqual(self.peer.id, "peer1")
        self.assertEqual(len(self.peer.blocks), 0)

if __name__ == "__main__":
    unittest.main()