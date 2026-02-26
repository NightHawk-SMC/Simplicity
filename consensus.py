"""
FCU Blockchain Consensus Mechanisms:
- Proof of Capacity (PoC): Primary mining based on donated storage
- Proof of Stake (PoS): Security layer with council + treasurer
- Proof of Work (PoW) Lottery: Randomization for reward distribution
"""

import hashlib
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PoCDifficulty:
    """Proof of Capacity difficulty adjustment (Signum-style)"""
    
    INITIAL_DIFFICULTY = 4
    TARGET_BLOCK_TIME = 22.5  # seconds (15-30s range, middle target)
    DIFFICULTY_ADJUSTMENT_BLOCKS = 50
    
    @staticmethod
    def calculate_new_difficulty(
        current_difficulty: int,
        actual_block_times: List[float],
        network_capacity_gb: float
    ) -> int:
        """
        Adjust Proof of Capacity difficulty based on:
        - Actual block times vs target
        - Overall network storage capacity
        
        Similar to Signum's mechanism
        """
        if len(actual_block_times) < 2:
            return current_difficulty
        
        # Calculate average block time
        avg_time = sum(actual_block_times) / len(actual_block_times)
        
        # If blocks are too fast, increase difficulty
        if avg_time < PoCDifficulty.TARGET_BLOCK_TIME * 0.8:
            return min(current_difficulty + 1, 32)
        
        # If blocks are too slow, decrease difficulty
        if avg_time > PoCDifficulty.TARGET_BLOCK_TIME * 1.2:
            return max(current_difficulty - 1, 1)
        
        return current_difficulty

    @staticmethod
    def verify_pow_solution(
        previous_hash: str,
        storage_capacity_gb: float,
        nonce: int,
        difficulty: int
    ) -> bool:
        """
        Verify PoC solution using storage-based proof.
        In production, this would verify against actual storage plots (Signum-style).
        
        Here we simulate: hash(previous_hash || capacity || nonce) must have
        'difficulty' leading zeros, weighted by capacity.
        """
        block_data = f"{previous_hash}:{storage_capacity_gb}:{nonce}"
        result_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
        # Check if hash meets difficulty target (leading zeros)
        required_leading_zeros = max(1, int(difficulty / 2))
        return result_hash.startswith('0' * required_leading_zeros)


class PoCMiner:
    """Proof of Capacity Miner"""
    
    def __init__(self, miner_id: str, storage_capacity_gb: float):
        self.miner_id = miner_id
        self.storage_capacity_gb = max(32.0, storage_capacity_gb)  # Minimum 32GB
        self.total_blocks_mined = 0
        self.last_mine_time = time.time()

    def mine_block(
        self,
        previous_hash: str,
        difficulty: int = PoCDifficulty.INITIAL_DIFFICULTY,
        timeout: float = 30.0
    ) -> Tuple[Optional[int], float]:
        """
        Mine a block using Proof of Capacity.
        
        Returns: (nonce, time_taken) or (None, 0) if timeout
        """
        start_time = time.time()
        nonce = 0
        
        while time.time() - start_time < timeout:
            if PoCDifficulty.verify_pow_solution(
                previous_hash,
                self.storage_capacity_gb,
                nonce,
                difficulty
            ):
                time_taken = time.time() - start_time
                self.total_blocks_mined += 1
                self.last_mine_time = time.time()
                return nonce, time_taken
            
            nonce += 1
        
        return None, time.time() - start_time

    def get_mining_probability(self, total_network_capacity_gb: float) -> float:
        """
        Mining probability based on storage capacity share.
        Proportional to: (miner_capacity / total_capacity)
        """
        if total_network_capacity_gb == 0:
            return 0.0
        return self.storage_capacity_gb / total_network_capacity_gb


class PoSValidator:
    """Proof of Stake Validator (Council member or Treasurer)"""
    
    ROLE_TREASURER = "treasurer"
    ROLE_COUNCIL = "council"
    ROLE_VALIDATOR = "validator"  # Regular staker
    
    def __init__(
        self,
        validator_id: str,
        role: str = ROLE_VALIDATOR,
        min_stake: float = 1000.0
    ):
        self.validator_id = validator_id
        self.role = role
        self.min_stake = min_stake
        self.total_staked = 0.0
        self.blocks_validated = 0
        self.slashing_count = 0

    def has_sufficient_stake(self) -> bool:
        """Check if validator has minimum required stake"""
        return self.total_stake() >= self.min_stake

    def total_stake(self) -> float:
        """Get total staked amount"""
        return self.total_staked

    def can_propose_block(self) -> bool:
        """
        Only treasurer and council can propose blocks.
        Council members need minimum stake.
        Treasurer is always able (system role).
        """
        if self.role == self.ROLE_TREASURER:
            return True
        
        if self.role == self.ROLE_COUNCIL:
            return self.has_sufficient_stake()
        
        return False

    def validate_block(self, block_hash: str) -> bool:
        """Sign/validate a block"""
        self.blocks_validated += 1
        return True

    def apply_slashing(self, amount: float):
        """Apply stake penalty (slashing) for misbehavior"""
        self.total_staked = max(0, self.total_staked - amount)
        self.slashing_count += 1


class PoSConsensus:
    """Proof of Stake consensus layer - Council governance"""
    
    def __init__(self, treasurer: PoSValidator):
        self.treasurer = treasurer
        self.council: Dict[str, PoSValidator] = {}  # 5 council members
        self.min_council_approval = 3  # Majority of 5
        self.pending_proposals: Dict[str, dict] = {}

    def add_council_member(self, member_id: str, validator: PoSValidator) -> bool:
        """Add council member (max 5)"""
        if len(self.council) >= 5:
            return False
        
        if member_id not in self.council:
            self.council[member_id] = validator
            return True
        
        return False

    def remove_council_member(self, member_id: str) -> bool:
        """Remove council member"""
        if member_id in self.council:
            del self.council[member_id]
            return True
        return False

    def get_validators(self) -> List[PoSValidator]:
        """Get all validators (treasurer + council)"""
        validators = [self.treasurer] + list(self.council.values())
        return validators

    def propose_block(
        self,
        block_hash: str,
        block_data: dict,
        proposer_id: str
    ) -> bool:
        """
        Treasurer proposes block parameters/rewards.
        Council has opportunity to vote.
        """
        if proposer_id == self.treasurer.validator_id:
            self.pending_proposals[block_hash] = {
                'data': block_data,
                'proposer': proposer_id,
                'votes': {},
                'timestamp': time.time()
            }
            return True
        
        return False

    def vote_on_proposal(
        self,
        block_hash: str,
        voter_id: str,
        vote: bool
    ) -> bool:
        """Council member votes on proposal"""
        if block_hash not in self.pending_proposals:
            return False
        
        if voter_id not in self.council and voter_id != self.treasurer.validator_id:
            return False
        
        self.pending_proposals[block_hash]['votes'][voter_id] = vote
        return True

    def count_votes(self, block_hash: str) -> Tuple[int, int, int]:
        """
        Count votes on proposal.
        Returns: (yes_votes, no_votes, total_voters)
        """
        if block_hash not in self.pending_proposals:
            return 0, 0, 0
        
        proposal = self.pending_proposals[block_hash]
        votes = proposal['votes']
        
        yes_votes = sum(1 for v in votes.values() if v is True)
        no_votes = sum(1 for v in votes.values() if v is False)
        
        return yes_votes, no_votes, len(self.council) + 1

    def is_proposal_approved(self, block_hash: str) -> bool:
        """Check if proposal has council approval"""
        yes_votes, no_votes, total = self.count_votes(block_hash)
        
        # Treasurer's proposal needs council approval
        if yes_votes >= self.min_council_approval:
            return True
        
        return False


class PoWLottery:
    """Proof of Work Lottery for Storage Donators"""
    
    def __init__(self, block_time: int = 22):
        self.block_time = block_time
        self.lottery_difficulty = 4
        self.participants: Dict[str, dict] = {}  # address -> lottery data
        self.winners: List[str] = []

    def register_participant(
        self,
        participant_id: str,
        storage_gb: float
    ):
        """Register storage donator for lottery"""
        self.participants[participant_id] = {
            'storage_gb': storage_gb,
            'entries': 0,
            'wins': 0,
            'last_entry_block': 0
        }

    def add_lottery_ticket(
        self,
        participant_id: str,
        block_height: int
    ) -> int:
        """
        Add lottery ticket for participant.
        More storage = more tickets per block.
        Returns number of tickets issued.
        """
        if participant_id not in self.participants:
            return 0
        
        # Tickets proportional to storage (32GB = 1 ticket minimum)
        capacity = self.participants[participant_id]['storage_gb']
        tickets = max(1, int(capacity / 32.0))
        
        self.participants[participant_id]['entries'] += tickets
        self.participants[participant_id]['last_entry_block'] = block_height
        
        return tickets

    def select_winner(self, block_hash: str, block_height: int) -> Optional[str]:
        """
        Select lottery winner for block.
        Uses block hash as entropy source.
        """
        if not self.participants:
            return None
        
        # Generate seed from block hash - ensure it's a valid integer
        hash_seed = hashlib.sha256(str(block_hash).encode()).hexdigest()
        seed = int(hash_seed[:16], 16)
        random.seed(seed)
        
        # Create weighted pool (proportional to storage)
        pool = []
        for participant_id, data in self.participants.items():
            # Weight by storage capacity
            weight = max(1, int(data['storage_gb'] / 32.0))
            pool.extend([participant_id] * weight)
        
        if not pool:
            return None
        
        winner = random.choice(pool)
        if winner not in self.winners:
            self.winners.append(winner)
        
        self.participants[winner]['wins'] += 1
        
        return winner

    def verify_pow_solution(
        self,
        participant_id: str,
        nonce: int,
        difficulty: int = 4
    ) -> bool:
        """Verify PoW solution for lottery entry"""
        if participant_id not in self.participants:
            return False
        
        data = f"{participant_id}:{nonce}".encode()
        result = hashlib.sha256(data).hexdigest()
        
        # Check leading zeros
        return result.startswith('0' * difficulty)

    def get_lottery_stats(self) -> Dict:
        """Get lottery statistics"""
        return {
            'total_participants': len(self.participants),
            'total_entries': sum(p['entries'] for p in self.participants.values()),
            'total_winners': len(self.winners),
            'top_winners': sorted(
                [(pid, p['wins']) for pid, p in self.participants.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
