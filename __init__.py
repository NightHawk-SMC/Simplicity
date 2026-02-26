"""
FCU Blockchain - Farmers Credit Union Multi-Node Blockchain
Version 1.0

Hybrid consensus combining:
- Proof of Capacity (PoC): Storage-based mining
- Proof of Stake (PoS): Council governance security
- Proof of Work (PoW): Lottery randomization

Package contents:
- core.py: Block, Blockchain, Transaction structures
- consensus.py: PoC, PoS, PoW Lottery mechanisms
- network.py: P2P networking, peer discovery, gossip
- node.py: FCU node implementations
- governance.py: Council voting and treasury management
- main.py: Network demonstration and CLI
"""

__version__ = "1.0.0"
__author__ = "Farmers Credit Union"

from .core import Block, Blockchain, Transaction, TransactionType
from .consensus import PoCMiner, PoSValidator, PoWLottery
from .network import PeerInfo, Message, MessageType
from .node import FCUNode, PoCMinerNode, PoSValidatorNode, FullNode
from .governance import GovernanceCouncil, Proposal, ProposalType

__all__ = [
    'Block', 'Blockchain', 'Transaction', 'TransactionType',
    'PoCMiner', 'PoSValidator', 'PoWLottery',
    'PeerInfo', 'Message', 'MessageType',
    'FCUNode', 'PoCMinerNode', 'PoSValidatorNode', 'FullNode',
    'GovernanceCouncil', 'Proposal', 'ProposalType'
]
