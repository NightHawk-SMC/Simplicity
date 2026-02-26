"""
FCU Blockchain P2P Network Layer
- Peer discovery and management
- Gossip-based message propagation
- Block and transaction synchronization
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict


class MessageType(Enum):
    """P2P message types"""
    PEER_HELLO = "peer_hello"              # Peer introduction
    PEER_DISCOVERY = "peer_discovery"      # Request/provide peer list
    BLOCK_ANNOUNCE = "block_announce"      # New block broadcast
    BLOCK_REQUEST = "block_request"        # Request specific block
    BLOCK_RESPONSE = "block_response"      # Block data response
    TRANSACTION = "transaction"            # New transaction
    SYNC_REQUEST = "sync_request"          # Request chain sync
    SYNC_RESPONSE = "sync_response"        # Chain state response
    VOTE_MESSAGE = "vote_message"          # Governance vote
    STORAGE_PLEDGE = "storage_pledge"      # Storage pledge announcement
    PING = "ping"                          # Keep-alive
    PONG = "pong"                          # Keep-alive response


@dataclass
class PeerInfo:
    """Information about a peer node"""
    peer_id: str                           # Unique peer identifier
    host: str                              # IP address
    port: int                              # P2P port
    node_type: str                         # "poc_miner", "pos_validator", "full_node"
    last_seen: float = field(default_factory=time.time)
    reputation: float = 1.0                # Peer reputation score (0-1)
    blocks_shared: int = 0
    failed_messages: int = 0
    version: str = "1.0"

    def is_alive(self, timeout: float = 300.0) -> bool:
        """Check if peer was seen recently"""
        return time.time() - self.last_seen < timeout

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Message:
    """P2P network message"""
    message_id: str                        # Unique message ID
    message_type: MessageType
    sender_id: str                         # Sender peer ID
    timestamp: float = field(default_factory=time.time)
    payload: Dict = field(default_factory=dict)
    ttl: int = 64                          # Time-to-live (hops)

    def hash(self) -> str:
        """Calculate message hash for deduplication"""
        data = {
            'sender_id': self.sender_id,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp,
            'payload_hash': hashlib.sha256(
                json.dumps(self.payload, sort_keys=True, default=str).encode()
            ).hexdigest()
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self) -> Dict:
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'payload': self.payload,
            'ttl': self.ttl
        }


class PeerDiscovery:
    """Peer discovery mechanism - Bootstrapping and peer exchange"""
    
    def __init__(self, bootstrap_peers: List[Tuple[str, int]] = None):
        self.bootstrap_peers = bootstrap_peers or [
            ("127.0.0.1", 8000),   # Bootstrap node 1
            ("127.0.0.1", 8001),   # Bootstrap node 2
        ]
        self.known_peers: Dict[str, PeerInfo] = {}
        self.peer_index: Dict[str, str] = {}  # host:port -> peer_id

    def add_peer(self, peer_info: PeerInfo) -> bool:
        """Add peer to known peers"""
        if peer_info.peer_id not in self.known_peers:
            self.known_peers[peer_info.peer_id] = peer_info
            self.peer_index[f"{peer_info.host}:{peer_info.port}"] = peer_info.peer_id
            return True
        
        # Update existing peer info
        self.known_peers[peer_info.peer_id] = peer_info
        return False

    def remove_peer(self, peer_id: str) -> bool:
        """Remove peer from known list"""
        if peer_id in self.known_peers:
            peer = self.known_peers[peer_id]
            key = f"{peer.host}:{peer.port}"
            if key in self.peer_index:
                del self.peer_index[key]
            del self.known_peers[peer_id]
            return True
        return False

    def get_random_peers(self, count: int = 5) -> List[PeerInfo]:
        """Get random peers for discovering more peers"""
        import random
        peers = list(self.known_peers.values())
        return random.sample(peers, min(count, len(peers)))

    def get_healthy_peers(self) -> List[PeerInfo]:
        """Get active peers with good reputation"""
        return [
            peer for peer in self.known_peers.values()
            if peer.is_alive() and peer.reputation > 0.5
        ]

    def update_peer_reputation(self, peer_id: str, success: bool):
        """Update peer reputation based on interaction"""
        if peer_id not in self.known_peers:
            return
        
        peer = self.known_peers[peer_id]
        if success:
            peer.reputation = min(1.0, peer.reputation + 0.05)
            peer.blocks_shared += 1
        else:
            peer.reputation = max(0.0, peer.reputation - 0.1)
            peer.failed_messages += 1
        
        peer.last_seen = time.time()

    def get_peer_count(self) -> int:
        """Get number of known peers"""
        return len(self.known_peers)

    def get_peers_by_type(self, node_type: str) -> List[PeerInfo]:
        """Get peers of specific type"""
        return [
            peer for peer in self.known_peers.values()
            if peer.node_type == node_type
        ]


class GossipProtocol:
    """Gossip-based message propagation"""
    
    def __init__(self, max_fanout: int = 5, max_history: int = 1000):
        self.max_fanout = max_fanout          # Max peers to gossip to
        self.message_history: Set[str] = set()  # Seen message hashes
        self.max_history = max_history
        self.message_queue: List[Message] = []

    def should_propagate(self, message: Message) -> bool:
        """Check if message should be propagated"""
        msg_hash = message.hash()
        
        if msg_hash in self.message_history:
            return False
        
        if message.ttl <= 0:
            return False
        
        return True

    def add_to_history(self, message: Message):
        """Add message to deduplication history"""
        msg_hash = message.hash()
        self.message_history.add(msg_hash)
        
        # Limit history size
        if len(self.message_history) > self.max_history:
            self.message_history = set(list(self.message_history)[-self.max_history:])

    def select_propagation_targets(
        self,
        available_peers: List[PeerInfo],
        exclude_peer: Optional[str] = None
    ) -> List[PeerInfo]:
        """
        Select targets for gossip propagation.
        Uses random sampling with reputation weighting.
        """
        import random
        
        # Filter out sender
        targets = [p for p in available_peers if p.peer_id != exclude_peer]
        
        if not targets:
            return []
        
        # Weight by reputation
        weights = [max(0.1, p.reputation) for p in targets]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return random.sample(targets, min(self.max_fanout, len(targets)))
        
        selected = []
        for _ in range(min(self.max_fanout, len(targets))):
            rand = random.uniform(0, total_weight)
            cumsum = 0
            for peer, weight in zip(targets, weights):
                cumsum += weight
                if rand <= cumsum:
                    selected.append(peer)
                    targets.remove(peer)
                    weights.remove(weight)
                    total_weight -= weight
                    break
        
        return selected

    def add_message(self, message: Message):
        """Add message to propagation queue"""
        if self.should_propagate(message):
            self.message_queue.append(message)
            self.add_to_history(message)

    def get_propagation_batch(self, batch_size: int = 10) -> List[Message]:
        """Get next batch of messages to propagate"""
        batch = self.message_queue[:batch_size]
        self.message_queue = self.message_queue[batch_size:]
        return batch


class MemoryPool:
    """Mempool - transaction and block synchronization pool"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.pending_transactions: Dict[str, dict] = {}
        self.pending_blocks: Dict[str, dict] = {}
        self.tx_index: Dict[str, str] = {}  # tx_id -> block_hash if included
        self.received_hashes: Set[str] = set()

    def add_transaction(self, tx_data: Dict) -> bool:
        """Add transaction to mempool"""
        if len(self.pending_transactions) >= self.max_size:
            return False
        
        tx_id = tx_data.get('tx_id')
        if tx_id in self.pending_transactions:
            return False
        
        self.pending_transactions[tx_id] = tx_data
        self.received_hashes.add(tx_id)
        return True

    def add_block(self, block_data: Dict) -> bool:
        """Add block to pending blocks"""
        block_hash = block_data.get('hash')
        if block_hash in self.pending_blocks:
            return False
        
        self.pending_blocks[block_hash] = block_data
        self.received_hashes.add(block_hash)
        return True

    def get_pending_transactions(self, limit: int = 100) -> List[Dict]:
        """Get pending transactions for block inclusion"""
        return list(self.pending_transactions.values())[:limit]

    def get_pending_block(self, block_hash: str) -> Optional[Dict]:
        """Get pending block by hash"""
        return self.pending_blocks.get(block_hash)

    def remove_transaction(self, tx_id: str) -> bool:
        """Remove included transaction from mempool"""
        if tx_id in self.pending_transactions:
            del self.pending_transactions[tx_id]
            return True
        return False

    def has_seen(self, item_hash: str) -> bool:
        """Check if we've seen this item"""
        return item_hash in self.received_hashes

    def get_stats(self) -> Dict:
        """Get mempool statistics"""
        return {
            'pending_transactions': len(self.pending_transactions),
            'pending_blocks': len(self.pending_blocks),
            'total_seen': len(self.received_hashes)
        }


class NetworkSyncer:
    """Synchronize blockchain state across nodes"""
    
    def __init__(self, max_batch_size: int = 50):
        self.max_batch_size = max_batch_size
        self.sync_in_progress = False
        self.last_sync_time = 0
        self.sync_peers: Set[str] = set()

    def start_sync(self) -> bool:
        """Start synchronization if not already running"""
        if self.sync_in_progress:
            return False
        
        self.sync_in_progress = True
        self.last_sync_time = time.time()
        return True

    def finish_sync(self):
        """Mark synchronization complete"""
        self.sync_in_progress = False

    def request_blocks(
        self,
        start_height: int,
        end_height: int
    ) -> Dict:
        """Create block request"""
        return {
            'start_height': start_height,
            'end_height': end_height,
            'batch_size': min(self.max_batch_size, end_height - start_height + 1)
        }

    def is_syncing(self) -> bool:
        """Check if currently syncing"""
        return self.sync_in_progress

    def get_sync_progress(self) -> float:
        """Get synchronization progress (0-1)"""
        if not self.sync_in_progress:
            return 1.0
        
        time_elapsed = time.time() - self.last_sync_time
        # Rough progress estimate (assume 5 min for full sync)
        return min(1.0, time_elapsed / 300.0)
