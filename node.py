"""
FCU Blockchain Node Implementations
- PoC Miner Node (storage-based mining)
- PoS Validator Node (council + treasurer)
- Full Node (complete blockchain state)
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core import (
    Blockchain, Block, Transaction, TransactionType,
    StoragePledge, PoSStake
)
from consensus import (
    PoCMiner, PoSValidator, PoSConsensus, PoWLottery,
    PoCDifficulty
)
from network import (
    PeerDiscovery, GossipProtocol, MemoryPool, NetworkSyncer,
    Message, MessageType, PeerInfo
)


class FCUNode:
    """Base FCU Blockchain Node"""
    
    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 8000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.blockchain = Blockchain()
        self.peer_discovery = PeerDiscovery()
        self.gossip = GossipProtocol()
        self.mempool = MemoryPool()
        self.syncer = NetworkSyncer()
        self.node_info = PeerInfo(
            peer_id=node_id,
            host=host,
            port=port,
            node_type="full_node",
            version="1.0"
        )
        self.connected_peers: Dict[str, PeerInfo] = {}
        self.block_times: List[float] = []

    def connect_peer(self, peer_info: PeerInfo) -> bool:
        """Connect to another peer"""
        self.connected_peers[peer_info.peer_id] = peer_info
        self.peer_discovery.add_peer(peer_info)
        return True

    def disconnect_peer(self, peer_id: str) -> bool:
        """Disconnect from peer"""
        if peer_id in self.connected_peers:
            del self.connected_peers[peer_id]
            return True
        return False

    def broadcast_message(
        self,
        message: Message,
        exclude_peer: Optional[str] = None
    ) -> int:
        """
        Broadcast message to peers using gossip.
        Returns number of peers message was sent to.
        """
        self.gossip.add_message(message)
        
        available_peers = [
            p for p in self.connected_peers.values()
            if p.peer_id != exclude_peer and p.is_alive()
        ]
        
        targets = self.gossip.select_propagation_targets(available_peers, exclude_peer)
        return len(targets)

    def receive_message(self, message: Message) -> bool:
        """Receive message from peer"""
        if not self.gossip.should_propagate(message):
            return False
        
        self.gossip.add_to_history(message)
        
        # Decrement TTL and re-broadcast if TTL > 0
        message.ttl -= 1
        if message.ttl > 0:
            self.broadcast_message(message, message.sender_id)
        
        return True

    def receive_transaction(self, tx_data: Dict) -> bool:
        """Receive transaction from network"""
        if self.mempool.add_transaction(tx_data):
            # Broadcast to peers
            message = Message(
                message_id=f"tx_{tx_data.get('tx_id')}",
                message_type=MessageType.TRANSACTION,
                sender_id=self.node_id,
                payload=tx_data
            )
            self.broadcast_message(message)
            return True
        return False

    def receive_block(self, block_data: Dict) -> bool:
        """Receive block from network"""
        if self.mempool.add_block(block_data):
            # Broadcast to peers
            message = Message(
                message_id=f"blk_{block_data.get('hash')}",
                message_type=MessageType.BLOCK_ANNOUNCE,
                sender_id=self.node_id,
                payload=block_data
            )
            self.broadcast_message(message)
            return True
        return False

    def sync_with_peer(self, peer_id: str) -> bool:
        """Request synchronization with peer"""
        if not self.syncer.start_sync():
            return False
        
        if peer_id not in self.connected_peers:
            self.syncer.finish_sync()
            return False
        
        print(f"[{self.node_id}] Syncing with {peer_id}...")
        self.syncer.finish_sync()
        return True

    def get_node_info(self) -> Dict:
        """Get node information"""
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'chain_height': self.blockchain.get_chain_length(),
            'connected_peers': len(self.connected_peers),
            'mempool_size': sum([
                len(self.mempool.pending_transactions),
                len(self.mempool.pending_blocks)
            ])
        }


class PoCMinerNode(FCUNode):
    """Proof of Capacity Miner Node"""
    
    def __init__(
        self,
        node_id: str,
        storage_gb: float = 256.0,
        host: str = "127.0.0.1",
        port: int = 8000
    ):
        super().__init__(node_id, host, port)
        self.node_info.node_type = "poc_miner"
        self.miner = PoCMiner(node_id, storage_gb)
        self.mining_rewards: Dict[str, float] = {}
        self.is_mining = False
        self.mining_difficulty = PoCDifficulty.INITIAL_DIFFICULTY

    def update_mining_difficulty(self):
        """Update PoC difficulty based on block times"""
        if len(self.block_times) >= PoCDifficulty.DIFFICULTY_ADJUSTMENT_BLOCKS:
            recent_times = self.block_times[-PoCDifficulty.DIFFICULTY_ADJUSTMENT_BLOCKS:]
            network_capacity = self._estimate_network_capacity()
            
            self.mining_difficulty = PoCDifficulty.calculate_new_difficulty(
                self.mining_difficulty,
                recent_times,
                network_capacity
            )

    def _estimate_network_capacity(self) -> float:
        """Estimate total network storage capacity"""
        # Estimate from connected miners
        capacity = self.miner.storage_capacity_gb
        for peer in self.connected_peers.values():
            if peer.node_type == "poc_miner":
                capacity += 256.0  # Assume 256GB per miner (placeholder)
        return capacity

    def mine_block(self) -> Optional[Block]:
        """Mine new block using PoC"""
        if self.is_mining:
            return None
        
        self.is_mining = True
        
        try:
            # Get pending transactions
            pending_txs = self.mempool.get_pending_transactions(limit=100)
            
            if not pending_txs:
                # Create empty block if no transactions
                pending_txs = []
            
            # Convert pending tx data to Transaction objects
            transactions = []
            for tx_data in pending_txs:
                # In real implementation, reconstruct Transaction object
                pass
            
            # Mine block
            latest_block = self.blockchain.get_latest_block()
            prev_hash = latest_block.hash
            
            start_time = time.time()
            nonce, mine_time = self.miner.mine_block(
                prev_hash,
                self.mining_difficulty,
                timeout=30.0
            )
            
            if nonce is None:
                return None
            
            # Create new block
            new_block = Block(
                index=latest_block.index + 1,
                previous_hash=prev_hash,
                timestamp=time.time(),
                transactions=transactions,
                miner=self.miner.miner_id,
                validators=[],  # Will be filled by PoS validators
                poc_difficulty=self.mining_difficulty,
                nonce=nonce
            )
            
            self.block_times.append(mine_time)
            self.blockchain.chain.append(new_block)
            
            # Update difficulty
            self.update_mining_difficulty()
            
            # Broadcast block
            message = Message(
                message_id=f"blk_{new_block.hash}",
                message_type=MessageType.BLOCK_ANNOUNCE,
                sender_id=self.node_id,
                payload=new_block.to_dict()
            )
            self.broadcast_message(message)
            
            return new_block
        
        finally:
            self.is_mining = False

    def get_mining_stats(self) -> Dict:
        """Get miner statistics"""
        return {
            'node_id': self.node_id,
            'storage_capacity_gb': self.miner.storage_capacity_gb,
            'blocks_mined': self.miner.total_blocks_mined,
            'current_difficulty': self.mining_difficulty,
            'avg_block_time': sum(self.block_times) / len(self.block_times) if self.block_times else 0,
            'mining_rewards': sum(self.mining_rewards.values())
        }


class PoSValidatorNode(FCUNode):
    """Proof of Stake Validator Node (Council or Treasurer)"""
    
    def __init__(
        self,
        node_id: str,
        role: str = PoSValidator.ROLE_VALIDATOR,
        initial_stake: float = 5000.0,
        host: str = "127.0.0.1",
        port: int = 8000
    ):
        super().__init__(node_id, host, port)
        self.node_info.node_type = "pos_validator"
        self.validator = PoSValidator(node_id, role, min_stake=1000.0)
        self.validator.total_staked = initial_stake
        self.blockchain.state[node_id] = initial_stake
        self.validation_rewards: Dict[str, float] = {}

    def validate_block(self, block_data: Dict) -> bool:
        """Validate and sign block"""
        if not self.validator.can_propose_block():
            return False
        
        # Verify block integrity
        block_hash = block_data.get('hash')
        
        # Sign block
        signature = self._sign_block(block_hash)
        
        # Broadcast validation
        message = Message(
            message_id=f"validate_{block_hash}",
            message_type=MessageType.VOTE_MESSAGE,
            sender_id=self.node_id,
            payload={
                'block_hash': block_hash,
                'validator_id': self.validator.validator_id,
                'signature': signature,
                'timestamp': time.time()
            }
        )
        self.broadcast_message(message)
        
        self.validator.validate_block(block_hash)
        return True

    def propose_governance_vote(
        self,
        proposal_id: str,
        proposal_data: Dict
    ) -> bool:
        """Propose governance vote (treasurer only)"""
        if self.validator.role != PoSValidator.ROLE_TREASURER:
            return False
        
        message = Message(
            message_id=f"vote_{proposal_id}",
            message_type=MessageType.VOTE_MESSAGE,
            sender_id=self.node_id,
            payload={
                'proposal_id': proposal_id,
                'proposal_data': proposal_data,
                'proposer': self.validator.validator_id,
                'timestamp': time.time()
            }
        )
        self.broadcast_message(message)
        return True

    def cast_governance_vote(
        self,
        proposal_id: str,
        vote: bool
    ) -> bool:
        """Cast governance vote (council only)"""
        if self.validator.role != PoSValidator.ROLE_COUNCIL:
            return False
        
        message = Message(
            message_id=f"vote_{proposal_id}_{self.node_id}",
            message_type=MessageType.VOTE_MESSAGE,
            sender_id=self.node_id,
            payload={
                'proposal_id': proposal_id,
                'vote': vote,
                'voter': self.validator.validator_id,
                'timestamp': time.time()
            }
        )
        self.broadcast_message(message)
        return True

    def _sign_block(self, block_hash: str) -> str:
        """Create signature for block (simplified)"""
        data = f"{self.validator.validator_id}:{block_hash}:{time.time()}".encode()
        return hashlib.sha256(data).hexdigest()[:32]

    def get_validator_stats(self) -> Dict:
        """Get validator statistics"""
        return {
            'node_id': self.node_id,
            'role': self.validator.role,
            'total_staked': self.validator.total_staked,
            'blocks_validated': self.validator.blocks_validated,
            'slashing_count': self.validator.slashing_count,
            'reputation': self.node_info.reputation,
            'validation_rewards': sum(self.validation_rewards.values())
        }


class FullNode(FCUNode):
    """Full Node - Maintains complete blockchain state"""
    
    def __init__(
        self,
        node_id: str,
        host: str = "127.0.0.1",
        port: int = 8000
    ):
        super().__init__(node_id, host, port)
        self.node_info.node_type = "full_node"
        self.last_block_received = time.time()

    def validate_and_apply_block(self, block_data: Dict) -> bool:
        """Validate and apply block to blockchain"""
        try:
            # Verify block structure
            if not self._verify_block_structure(block_data):
                return False
            
            # Apply transactions
            transactions = block_data.get('transactions', [])
            for tx in transactions:
                self.blockchain.add_transaction(self._dict_to_transaction(tx))
            
            self.last_block_received = time.time()
            return True
        
        except Exception as e:
            print(f"Error applying block: {e}")
            return False

    def _verify_block_structure(self, block_data: Dict) -> bool:
        """Verify block structure and integrity"""
        required_fields = ['index', 'hash', 'previous_hash', 'timestamp', 'miner', 'validators']
        return all(field in block_data for field in required_fields)

    def _dict_to_transaction(self, tx_data: Dict) -> Transaction:
        """Convert dictionary to Transaction object"""
        return Transaction(
            tx_id=tx_data.get('tx_id'),
            timestamp=tx_data.get('timestamp'),
            sender=tx_data.get('sender'),
            receiver=tx_data.get('receiver'),
            amount=tx_data.get('amount'),
            tx_type=TransactionType(tx_data.get('tx_type', 'transfer')),
            nonce=tx_data.get('nonce', 0),
            signature=tx_data.get('signature'),
            data=tx_data.get('data', {})
        )

    def get_full_node_stats(self) -> Dict:
        """Get full node statistics"""
        return {
            'node_id': self.node_id,
            'chain_height': self.blockchain.get_chain_length(),
            'total_accounts': len(self.blockchain.state),
            'total_storage_pledges': len(self.blockchain.storage_pledges),
            'total_pos_stakes': sum(len(s) for s in self.blockchain.pos_stakes.values()),
            'connected_peers': len(self.connected_peers),
            'mempool_transactions': len(self.mempool.pending_transactions),
            'last_block_received': self.last_block_received
        }
