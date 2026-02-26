"""
Farmers Credit Union (FCU) Blockchain - Core Data Structures
Hybrid consensus: Proof of Capacity (PoC) + Proof of Stake (PoS) + Proof of Work (PoW) Lottery
"""

import time
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TransactionType(Enum):
    """Transaction types in FCU blockchain"""
    TRANSFER = "transfer"              # Standard token transfer
    STAKE_DEPOSIT = "stake_deposit"    # PoS stake deposit
    STAKE_WITHDRAW = "stake_withdraw"  # PoS stake withdrawal
    STORAGE_PLEDGE = "storage_pledge"  # PoC storage commitment
    STORAGE_REVOKE = "storage_revoke"  # PoC storage revocation
    GOVERNANCE_VOTE = "governance_vote" # Council voting


@dataclass
class Transaction:
    """Transaction in FCU blockchain"""
    tx_id: str                          # Unique transaction ID
    timestamp: float                    # Transaction creation time
    sender: str                         # Sender wallet address
    receiver: str                       # Receiver wallet address
    amount: float                       # FCU tokens
    tx_type: TransactionType = TransactionType.TRANSFER
    nonce: int = 0                      # Prevent replay attacks
    signature: Optional[str] = None     # Digital signature
    data: Dict = field(default_factory=dict)  # Additional data (governance, storage, etc.)

    def to_dict(self) -> Dict:
        """Convert transaction to dictionary"""
        data = asdict(self)
        data['tx_type'] = self.tx_type.value
        return data

    def to_json(self) -> str:
        """Serialize transaction to JSON"""
        return json.dumps(self.to_dict(), default=str)

    def hash(self) -> str:
        """Calculate transaction hash"""
        value = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def create_genesis_tx() -> 'Transaction':
        """Create genesis transaction for initial token donation (Simcoin) from Simplicity Labs"""
        return Transaction(
            tx_id="GENESIS_SIMCOIN",
            timestamp=time.time(),
            sender="SYSTEM",
            receiver="FCU_TREASURY",
            amount=1000000.0,  # Simcoin donation from Simplicity Labs
            tx_type=TransactionType.TRANSFER,
            data={"note": "Genesis - Simcoin donation to FCU Treasury"}
        )


@dataclass
class StoragePledge:
    """Storage pledge for Proof of Capacity"""
    pledger: str                        # Storage donator's address
    capacity_gb: float                  # Pledged capacity in GB
    timestamp: float = field(default_factory=time.time)
    proof_hash: Optional[str] = None    # Storage availability proof (Signum-style)
    challenge_response: Optional[str] = None  # Response to challenge
    is_active: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PoSStake:
    """Proof of Stake stake information"""
    validator: str                      # Validator address
    amount: float                       # Staked FCU tokens
    lock_time: int = 0                  # Blocks until unlock
    timestamp: float = field(default_factory=time.time)
    delegated_from: Optional[str] = None  # If delegated
    is_active: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PoWLotteryEntry:
    """Proof of Work lottery entry for storage donators"""
    participant: str                    # Storage donator address
    nonce: int                          # Lottery nonce
    difficulty_target: str              # Mining target
    timestamp: float = field(default_factory=time.time)
    winning_nonce: Optional[int] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class Block:
    """Block in FCU multi-node blockchain"""
    
    def __init__(
        self,
        index: int,
        previous_hash: str,
        timestamp: float,
        transactions: List[Transaction],
        miner: str,                      # PoC miner address
        validators: List[str],           # PoS validators who approved block
        poc_difficulty: int = 4,         # PoC difficulty
        pow_lottery_winner: Optional[str] = None,
        nonce: int = 0,
        merkle_root: Optional[str] = None,
        state_root: Optional[str] = None
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.miner = miner                    # PoC miner
        self.validators = validators          # PoS signers (council + treasurer)
        self.poc_difficulty = poc_difficulty
        self.pow_lottery_winner = pow_lottery_winner
        self.nonce = nonce
        self.merkle_root = merkle_root or Block.calculate_merkle_root(self.transactions)
        self.state_root = state_root
        self.hash = self.calculate_hash()

    @staticmethod
    def calculate_merkle_root(transactions: List[Transaction]) -> str:
        """Calculate Merkle root of transactions"""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()
        
        tx_hashes = [tx.hash() for tx in transactions]
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            tx_hashes = [
                hashlib.sha256((tx_hashes[i] + tx_hashes[i+1]).encode()).hexdigest()
                for i in range(0, len(tx_hashes), 2)
            ]
        return tx_hashes[0]

    def calculate_hash(self) -> str:
        """Calculate block hash with all components"""
        block_data = {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'merkle_root': self.merkle_root,
            'miner': self.miner,
            'validators': sorted(self.validators),
            'poc_difficulty': self.poc_difficulty,
            'nonce': self.nonce,
            'state_root': self.state_root
        }
        block_json = json.dumps(block_data, sort_keys=True, default=str)
        return hashlib.sha256(block_json.encode()).hexdigest()

    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'hash': self.hash,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'miner': self.miner,
            'validators': self.validators,
            'poc_difficulty': self.poc_difficulty,
            'pow_lottery_winner': self.pow_lottery_winner,
            'nonce': self.nonce,
            'merkle_root': self.merkle_root,
            'state_root': self.state_root
        }

    def to_json(self) -> str:
        """Serialize block to JSON"""
        return json.dumps(self.to_dict(), default=str)


class Blockchain:
    """FCU Multi-node Blockchain with Hybrid Consensus"""
    
    def __init__(self, chain_id: str = "FCU_MAINNET"):
        self.chain_id = chain_id
        self.chain: List[Block] = []
        self.state: Dict[str, float] = {}  # Account balances
        self.storage_pledges: Dict[str, StoragePledge] = {}
        self.pos_stakes: Dict[str, List[PoSStake]] = {}
        self.pow_lottery_entries: Dict[int, List[PoWLotteryEntry]] = {}
        self.pending_transactions: List[Transaction] = []
        
        # Initialize with genesis block
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Create genesis block with initial Simcoin donation to FCU"""
        genesis_tx = Transaction.create_genesis_tx()
        genesis_block = Block(
            index=0,
            previous_hash="0",
            timestamp=time.time(),
            transactions=[genesis_tx],
            miner="GENESIS_SYSTEM",
            validators=["GENESIS_SYSTEM"],
            poc_difficulty=1,
            nonce=0
        )
        self.chain.append(genesis_block)
        self.state[genesis_tx.receiver] = genesis_tx.amount

    def get_latest_block(self) -> Block:
        """Get the last block in the chain"""
        return self.chain[-1]

    def get_balance(self, address: str) -> float:
        """Get account balance"""
        return self.state.get(address, 0.0)

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool"""
        if self.get_balance(transaction.sender) >= transaction.amount:
            self.pending_transactions.append(transaction)
            return True
        return False

    def process_transactions(self, transactions: List[Transaction]):
        """Apply transactions to state"""
        for tx in transactions:
            if tx.tx_type == TransactionType.TRANSFER:
                sender_bal = self.state.get(tx.sender, 0.0)
                if sender_bal >= tx.amount:
                    self.state[tx.sender] = sender_bal - tx.amount
                    self.state[tx.receiver] = self.state.get(tx.receiver, 0.0) + tx.amount
            elif tx.tx_type == TransactionType.STAKE_DEPOSIT:
                if tx.sender in self.pos_stakes:
                    self.pos_stakes[tx.sender].append(PoSStake(
                        validator=tx.sender,
                        amount=tx.amount
                    ))
                else:
                    self.pos_stakes[tx.sender] = [PoSStake(
                        validator=tx.sender,
                        amount=tx.amount
                    )]
                self.state[tx.sender] = self.state.get(tx.sender, 0.0) - tx.amount
            elif tx.tx_type == TransactionType.STORAGE_PLEDGE:
                self.storage_pledges[tx.sender] = StoragePledge(
                    pledger=tx.sender,
                    capacity_gb=tx.data.get('capacity_gb', 32.0),
                    proof_hash=tx.data.get('proof_hash')
                )

    def validate_chain(self) -> bool:
        """Validate entire blockchain integrity"""
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check hash integrity
            if block.hash != block.calculate_hash():
                return False
            
            # Check chain continuity
            if block.previous_hash != previous_block.hash:
                return False
        
        return True

    def get_chain_length(self) -> int:
        """Get blockchain length"""
        return len(self.chain)

    def print_chain(self, verbose: bool = False):
        """Print blockchain contents"""
        for block in self.chain:
            print(f"\n{'='*60}")
            print(f"Block #{block.index}")
            print(f"Hash: {block.hash}")
            print(f"Previous Hash: {block.previous_hash}")
            print(f"Timestamp: {block.timestamp}")
            print(f"Miner (PoC): {block.miner}")
            print(f"Validators (PoS): {', '.join(block.validators)}")
            print(f"PoC Difficulty: {block.poc_difficulty}")
            print(f"PoW Lottery Winner: {block.pow_lottery_winner}")
            print(f"Merkle Root: {block.merkle_root}")
            print(f"Transactions: {len(block.transactions)}")
            
            if verbose:
                for i, tx in enumerate(block.transactions):
                    print(f"  TX{i}: {tx.sender} -> {tx.receiver}: {tx.amount} FCU ({tx.tx_type.value})")
            print(f"{'='*60}")
