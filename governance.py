"""
FCU Blockchain Governance System
- Council proposal and voting
- Reward distribution management
- Treasury operations
- Difficulty and parameter adjustments
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ProposalType(Enum):
    """Types of governance proposals"""
    REWARD_ADJUSTMENT = "reward_adjustment"
    DIFFICULTY_TUNING = "difficulty_tuning"
    PARAMETER_CHANGE = "parameter_change"
    TREASURY_SPENDING = "treasury_spending"
    VALIDATOR_REMOVAL = "validator_removal"
    STORAGE_REQUIREMENT = "storage_requirement"


class ProposalStatus(Enum):
    """Proposal lifecycle status"""
    PROPOSED = "proposed"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class Proposal:
    """Governance proposal"""
    proposal_id: str
    proposal_type: ProposalType
    proposer: str                          # Treasurer address
    description: str
    proposed_changes: Dict                 # What is being changed
    timestamp: float = field(default_factory=time.time)
    voting_deadline: float = field(default_factory=lambda: time.time() + 86400)  # 24h
    status: ProposalStatus = ProposalStatus.PROPOSED
    votes: Dict[str, bool] = field(default_factory=dict)  # voter_id -> vote (yes/no)
    execution_time: Optional[float] = None

    def is_voting_active(self) -> bool:
        """Check if voting period is still active"""
        return time.time() < self.voting_deadline and self.status == ProposalStatus.VOTING

    def get_vote_count(self) -> Tuple[int, int]:
        """Get (yes_votes, no_votes)"""
        yes = sum(1 for v in self.votes.values() if v is True)
        no = sum(1 for v in self.votes.values() if v is False)
        return yes, no

    def is_approved(self, min_approval: int = 3) -> bool:
        """Check if proposal has sufficient approval (3/5 council)"""
        yes, no = self.get_vote_count()
        return yes >= min_approval

    def to_dict(self) -> Dict:
        return {
            'proposal_id': self.proposal_id,
            'proposal_type': self.proposal_type.value,
            'proposer': self.proposer,
            'description': self.description,
            'proposed_changes': self.proposed_changes,
            'timestamp': self.timestamp,
            'voting_deadline': self.voting_deadline,
            'status': self.status.value,
            'votes': self.votes,
            'yes_votes': self.get_vote_count()[0],
            'no_votes': self.get_vote_count()[1]
        }


@dataclass
class RewardConfiguration:
    """Block reward configuration"""
    poc_miner_reward: float = 10.0         # Reward for block miner
    pos_validator_reward: float = 5.0      # Reward per validator
    pow_lottery_reward: float = 2.0        # Lottery winner reward
    storage_reward_per_gb: float = 0.1     # Annual reward per GB pledged
    base_transaction_fee: float = 0.01     # Base fee per transaction
    timestamp: float = field(default_factory=time.time)
    activated_block: int = 0               # Block height when activated

    def to_dict(self) -> Dict:
        return {
            'poc_miner_reward': self.poc_miner_reward,
            'pos_validator_reward': self.pos_validator_reward,
            'pow_lottery_reward': self.pow_lottery_reward,
            'storage_reward_per_gb': self.storage_reward_per_gb,
            'base_transaction_fee': self.base_transaction_fee,
            'timestamp': self.timestamp,
            'activated_block': self.activated_block
        }


class Treasury:
    """FCU Treasury - manages funds and allocations"""
    
    def __init__(self, initial_balance: float = 1000000.0):
        self.balance = initial_balance
        self.transactions: List[Dict] = []
        self.allocations: Dict[str, float] = {}
        self.spending_history: List[Dict] = []

    def allocate_funds(self, purpose: str, amount: float) -> bool:
        """Allocate funds for specific purpose"""
        if amount > self.balance:
            return False
        
        self.allocations[purpose] = self.allocations.get(purpose, 0) + amount
        self.balance -= amount
        
        self.transactions.append({
            'type': 'allocation',
            'purpose': purpose,
            'amount': amount,
            'timestamp': time.time()
        })
        
        return True

    def spend_from_allocation(self, purpose: str, amount: float, recipient: str) -> bool:
        """Spend allocated funds"""
        if purpose not in self.allocations or self.allocations[purpose] < amount:
            return False
        
        self.allocations[purpose] -= amount
        
        self.spending_history.append({
            'purpose': purpose,
            'amount': amount,
            'recipient': recipient,
            'timestamp': time.time()
        })
        
        self.transactions.append({
            'type': 'spending',
            'purpose': purpose,
            'amount': amount,
            'recipient': recipient,
            'timestamp': time.time()
        })
        
        return True

    def receive_funds(self, amount: float, source: str):
        """Receive funds (block rewards, donations)"""
        self.balance += amount
        self.transactions.append({
            'type': 'income',
            'source': source,
            'amount': amount,
            'timestamp': time.time()
        })

    def get_balance(self) -> float:
        """Get current treasury balance"""
        return self.balance

    def get_allocated_amount(self) -> float:
        """Get total allocated funds"""
        return sum(self.allocations.values())

    def get_unallocated_amount(self) -> float:
        """Get unallocated treasury funds"""
        return self.balance - self.get_allocated_amount()

    def get_allocation_status(self) -> Dict:
        """Get allocation status"""
        return {
            'total_balance': self.balance,
            'allocated': self.get_allocated_amount(),
            'unallocated': self.get_unallocated_amount(),
            'allocations': self.allocations,
            'transaction_count': len(self.transactions)
        }


class GovernanceCouncil:
    """Council governance system"""
    
    def __init__(self, treasurer_id: str, council_members: List[str]):
        self.treasurer_id = treasurer_id
        self.council_members = council_members[:5]  # Max 5 members
        self.proposals: Dict[str, Proposal] = {}
        self.treasury = Treasury()
        self.reward_config = RewardConfiguration()
        self.proposal_counter = 0
        self.parameter_history: List[Dict] = []

    def create_proposal(
        self,
        proposal_type: ProposalType,
        description: str,
        proposed_changes: Dict,
        voting_period_hours: int = 24
    ) -> Optional[str]:
        """Create new governance proposal"""
        self.proposal_counter += 1
        proposal_id = f"PROP_{self.proposal_counter:06d}"
        
        proposal = Proposal(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            proposer=self.treasurer_id,
            description=description,
            proposed_changes=proposed_changes,
            voting_deadline=time.time() + (voting_period_hours * 3600)
        )
        
        self.proposals[proposal_id] = proposal
        proposal.status = ProposalStatus.VOTING
        
        print(f"Created proposal {proposal_id}: {description}")
        return proposal_id

    def vote_on_proposal(
        self,
        proposal_id: str,
        voter_id: str,
        vote: bool
    ) -> bool:
        """Cast vote on proposal"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        # Only council members can vote
        if voter_id not in self.council_members:
            return False
        
        # Check if voting is active
        if not proposal.is_voting_active():
            return False
        
        # Record vote
        proposal.votes[voter_id] = vote
        
        # Check if proposal can be finalized
        if len(proposal.votes) >= len(self.council_members):
            self._finalize_proposal(proposal_id)
        
        return True

    def _finalize_proposal(self, proposal_id: str):
        """Finalize proposal after voting complete"""
        proposal = self.proposals[proposal_id]
        
        if proposal.is_approved(min_approval=3):  # 3 of 5 required
            proposal.status = ProposalStatus.APPROVED
            self._execute_proposal(proposal_id)
        else:
            proposal.status = ProposalStatus.REJECTED

    def _execute_proposal(self, proposal_id: str):
        """Execute approved proposal"""
        proposal = self.proposals[proposal_id]
        proposal.execution_time = time.time()
        
        if proposal.proposal_type == ProposalType.REWARD_ADJUSTMENT:
            self._apply_reward_changes(proposal.proposed_changes)
        elif proposal.proposal_type == ProposalType.TREASURY_SPENDING:
            self._apply_treasury_spending(proposal.proposed_changes)
        elif proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
            self._apply_parameter_changes(proposal.proposed_changes)
        
        proposal.status = ProposalStatus.EXECUTED
        print(f"Executed proposal {proposal_id}")

    def _apply_reward_changes(self, changes: Dict):
        """Apply reward configuration changes"""
        for key, value in changes.items():
            if hasattr(self.reward_config, key):
                setattr(self.reward_config, key, value)
        
        self.parameter_history.append({
            'type': 'reward_adjustment',
            'changes': changes,
            'timestamp': time.time()
        })

    def _apply_treasury_spending(self, changes: Dict):
        """Process treasury spending approval"""
        recipient = changes.get('recipient')
        amount = changes.get('amount')
        purpose = changes.get('purpose', 'governance_approved')
        
        if recipient and amount:
            self.treasury.spend_from_allocation(purpose, amount, recipient)

    def _apply_parameter_changes(self, changes: Dict):
        """Apply parameter changes"""
        self.parameter_history.append({
            'type': 'parameter_change',
            'changes': changes,
            'timestamp': time.time()
        })

    def get_proposal_status(self, proposal_id: str) -> Optional[Dict]:
        """Get proposal status"""
        if proposal_id not in self.proposals:
            return None
        
        return self.proposals[proposal_id].to_dict()

    def get_all_proposals(self, status: Optional[ProposalStatus] = None) -> List[Dict]:
        """Get all proposals, optionally filtered by status"""
        proposals = list(self.proposals.values())
        
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        return [p.to_dict() for p in proposals]

    def get_governance_stats(self) -> Dict:
        """Get governance statistics"""
        return {
            'treasurer': self.treasurer_id,
            'council_members': len(self.council_members),
            'council_list': self.council_members,
            'total_proposals': len(self.proposals),
            'active_proposals': len([p for p in self.proposals.values() if p.status == ProposalStatus.VOTING]),
            'approved_proposals': len([p for p in self.proposals.values() if p.status == ProposalStatus.APPROVED]),
            'treasury_balance': self.treasury.get_balance(),
            'treasury_allocations': self.treasury.allocations,
            'current_rewards': self.reward_config.to_dict()
        }

    def distribute_block_rewards(
        self,
        miner: str,
        validators: List[str],
        lottery_winner: Optional[str] = None
    ) -> Dict:
        """Distribute block rewards to participants"""
        rewards_given = {}
        
        # Miner reward
        miner_reward = self.reward_config.poc_miner_reward
        rewards_given[miner] = miner_reward
        
        # Validator rewards
        validator_reward = self.reward_config.pos_validator_reward
        for validator in validators:
            rewards_given[validator] = validator_reward
        
        # Lottery reward
        if lottery_winner:
            lottery_reward = self.reward_config.pow_lottery_reward
            rewards_given[lottery_winner] = lottery_reward
        
        # Record distribution
        self.parameter_history.append({
            'type': 'reward_distribution',
            'block_height': 0,  # Would come from blockchain
            'rewards': rewards_given,
            'timestamp': time.time()
        })
        
        return rewards_given

    def adjust_difficulty(self, current_difficulty: int, adjustment: int) -> int:
        """Adjust PoC difficulty via governance"""
        new_difficulty = max(1, min(32, current_difficulty + adjustment))
        
        if new_difficulty != current_difficulty:
            self.parameter_history.append({
                'type': 'difficulty_adjustment',
                'old_difficulty': current_difficulty,
                'new_difficulty': new_difficulty,
                'timestamp': time.time()
            })
        
        return new_difficulty
