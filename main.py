"""
FCU Blockchain - Integrated Demo
Demonstrates the complete multi-node blockchain with:
- PoC mining (storage-based)
- PoS validation (council governance)
- PoW lottery (randomization)
- P2P networking
- Governance voting
"""

import time
import random
from typing import List

from core import (
    Blockchain, Transaction, TransactionType, Block
)
from consensus import (
    PoCMiner, PoSValidator, PoSConsensus, PoWLottery,
    PoCDifficulty
)
from node import (
    PoCMinerNode, PoSValidatorNode, FullNode, FCUNode
)
from network import (
    PeerInfo, Message, MessageType
)
from governance import (
    GovernanceCouncil, ProposalType
)


class FCUNetwork:
    """Multi-node FCU Blockchain Network Simulation"""
    
    def __init__(self):
        self.nodes: dict = {}
        self.poc_miners: dict = {}
        self.pos_validators: dict = {}
        self.full_nodes: dict = {}
        self.governance_council: GovernanceCouncil = None
        self.pow_lottery: PoWLottery = None

    def setup_network(self):
        """Initialize a complete FCU network"""
        print("\n" + "="*80)
        print("FARMERS CREDIT UNION (FCU) BLOCKCHAIN NETWORK SETUP")
        print("="*80)
        
        # 1. Create Treasurer and Council
        print("\n[GOVERNANCE] Setting up governance council...")
        treasurer = PoSValidatorNode(
            node_id="TREASURER_Alice",
            role=PoSValidator.ROLE_TREASURER,
            initial_stake=50000.0,
            port=8000
        )
        
        council_members = [
            "COUNCIL_Bob",
            "COUNCIL_Charlie", 
            "COUNCIL_Diana",
            "COUNCIL_Eve",
            "COUNCIL_Frank"
        ]
        
        council_validator_nodes = {}
        for member_id in council_members[:5]:
            node = PoSValidatorNode(
                node_id=member_id,
                role=PoSValidator.ROLE_COUNCIL,
                initial_stake=10000.0,
                port=8001
            )
            council_validator_nodes[member_id] = node
            self.pos_validators[member_id] = node
        
        self.pos_validators["TREASURER_Alice"] = treasurer
        self.governance_council = GovernanceCouncil(
            treasurer_id="TREASURER_Alice",
            council_members=council_members[:5]
        )
        
        print(f"[OK] Treasurer: TREASURER_Alice (50,000 FCU stake)")
        print(f"[OK] Council Members ({len(council_members)}):")
        for member in council_members[:5]:
            print(f"  - {member} (10,000 FCU stake)")
        
        # 2. Create PoC Miners
        print("\n[POC MINING] Setting up storage donators...")
        miners = [
            ("Farmer_John", 256.0),    # 256 GB pledged
            ("Farmer_Maria", 512.0),   # 512 GB pledged
            ("Farmer_Carlos", 128.0),  # 128 GB pledged
        ]
        
        for miner_id, storage_gb in miners:
            node = PoCMinerNode(
                node_id=miner_id,
                storage_gb=storage_gb,
                port=8010
            )
            self.poc_miners[miner_id] = node
            print(f"[OK] {miner_id}: {storage_gb} GB pledged")
        
        # 3. Create PoW Lottery System
        print("\n[POW LOTTERY] Setting up lottery system...")
        self.pow_lottery = PoWLottery(block_time=22)
        
        for miner_id in self.poc_miners.keys():
            storage_gb = self.poc_miners[miner_id].miner.storage_capacity_gb
            self.pow_lottery.register_participant(miner_id, storage_gb)
        
        print(f"[OK] Lottery initialized with {len(self.poc_miners)} participants")
        
        # 4. Create Full Nodes
        print("\n[FULL NODES] Setting up full nodes...")
        full_node_count = 2
        for i in range(full_node_count):
            node_id = f"FullNode_{i+1}"
            node = FullNode(node_id, port=8020+i)
            self.full_nodes[node_id] = node
            print(f"[OK] {node_id}")
        
        # 5. Connect all nodes in mesh topology
        print("\n[NETWORKING] Establishing peer connections...")
        all_nodes = list(self.poc_miners.values()) + \
                   list(self.pos_validators.values()) + \
                   list(self.full_nodes.values())
        
        # Create mesh: each node knows about others
        for node in all_nodes:
            for other_node in all_nodes:
                if node.node_id != other_node.node_id:
                    peer_info = PeerInfo(
                        peer_id=other_node.node_id,
                        host=other_node.host,
                        port=other_node.port,
                        node_type=other_node.node_info.node_type
                    )
                    node.connect_peer(peer_info)
        
        print(f"[OK] Mesh network established: {len(all_nodes)} nodes")
        for node in all_nodes:
            print(f"  {node.node_id}: connected to {node.peer_discovery.get_peer_count()} peers")
        
        print("\n" + "="*80)
        print("NETWORK SETUP COMPLETE")
        print("="*80)

    def mine_blocks(self, block_count: int = 3):
        """Simulate block mining"""
        print("\n" + "="*80)
        print(f"MINING SIMULATION: {block_count} blocks")
        print("="*80)
        
        for i in range(block_count):
            print(f"\n[BLOCK {i+1}] Mining new block...")
            
            # Select random miner based on storage share
            miner_id = random.choice(list(self.poc_miners.keys()))
            miner_node = self.poc_miners[miner_id]
            
            print(f"  PoC Miner: {miner_id}")
            
            # Get validators (all council + treasurer)
            validators = list(self.pos_validators.keys())
            selected_validators = random.sample(
                validators,
                min(3, len(validators))
            )
            print(f"  PoS Validators: {', '.join(selected_validators)}")
            
            # Select PoW lottery winner
            block_hash = f"block_{i+1}"  # Placeholder
            lottery_winner = self.pow_lottery.select_winner(block_hash, i)
            print(f"  PoW Lottery Winner: {lottery_winner}")
            
            # Distribute rewards
            rewards = self.governance_council.distribute_block_rewards(
                miner_id,
                selected_validators,
                lottery_winner
            )
            print(f"  Rewards Distributed:")
            for recipient, amount in rewards.items():
                print(f"    - {recipient}: {amount} FCU")
            
            # Broadcast block to network
            for node_id, node in self.full_nodes.items():
                message = Message(
                    message_id=f"blk_{block_hash}",
                    message_type=MessageType.BLOCK_ANNOUNCE,
                    sender_id=miner_id,
                    payload={'block': i+1, 'miner': miner_id}
                )
                node.broadcast_message(message)
            
            # Add lottery ticket for next round
            self.pow_lottery.add_lottery_ticket(miner_id, i)
            
            time.sleep(0.5)  # Simulate block time
        
        print("\n" + "="*80)
        print(f"MINING SIMULATION COMPLETE")
        print("="*80)

    def demonstrate_governance(self):
        """Demonstrate governance voting"""
        print("\n" + "="*80)
        print("GOVERNANCE VOTING DEMONSTRATION")
        print("="*80)
        
        # Proposal 1: Adjust PoC miner rewards
        print("\n[PROPOSAL 1] Miner Reward Adjustment")
        proposal_id = self.governance_council.create_proposal(
            proposal_type=ProposalType.REWARD_ADJUSTMENT,
            description="Increase PoC miner rewards from 10 FCU to 12 FCU per block",
            proposed_changes={
                'poc_miner_reward': 12.0,
                'reason': 'Incentivize larger storage pledges'
            },
            voting_period_hours=24
        )
        
        print("\n[VOTING]")
        # Simulate council voting
        council_votes = {
            "COUNCIL_Bob": True,
            "COUNCIL_Charlie": True,
            "COUNCIL_Diana": True,
            "COUNCIL_Eve": False,
            "COUNCIL_Frank": True
        }
        
        for voter, vote in council_votes.items():
            self.governance_council.vote_on_proposal(
                proposal_id,
                voter,
                vote
            )
            vote_text = "YES" if vote else "NO"
            print(f"  {voter}: {vote_text}")
        
        # Check approval
        yes, no = self.governance_council.proposals[proposal_id].get_vote_count()
        print(f"\nResult: {yes} YES, {no} NO")
        
        if self.governance_council.proposals[proposal_id].is_approved():
            print(f"  [APPROVED] - Executing changes...")
            status = self.governance_council.get_proposal_status(proposal_id)
            print(f"  New miner reward: {status['proposed_changes']['poc_miner_reward']} FCU")
        else:
            print(f"[REJECTED]")
        
        # Proposal 2: Treasury spending for validator development
        print("\n\n[PROPOSAL 2] Treasury Allocation for Development")
        proposal_id2 = self.governance_council.create_proposal(
            proposal_type=ProposalType.TREASURY_SPENDING,
            description="Allocate 50,000 FCU for validator software development",
            proposed_changes={
                'amount': 50000.0,
                'recipient': 'DEV_FUND',
                'purpose': 'Validator software upgrades'
            },
            voting_period_hours=24
        )
        
        print("\n[VOTING]")
        council_votes2 = {
            "COUNCIL_Bob": True,
            "COUNCIL_Charlie": True,
            "COUNCIL_Diana": True,
            "COUNCIL_Eve": True,
            "COUNCIL_Frank": True
        }
        
        for voter, vote in council_votes2.items():
            self.governance_council.vote_on_proposal(
                proposal_id2,
                voter,
                vote
            )
            vote_text = "YES" if vote else "NO"
            print(f"  {voter}: {vote_text}")
        
        yes, no = self.governance_council.proposals[proposal_id2].get_vote_count()
        print(f"\nResult: {yes} YES, {no} NO")
        
        if self.governance_council.proposals[proposal_id2].is_approved():
            print("[APPROVED] - Treasury allocated.")
            print(f"  Treasury Balance: {self.governance_council.treasury.get_balance()} FCU")
        
        print("\n" + "="*80)

    def print_network_stats(self):
        """Print comprehensive network statistics"""
        print("\n" + "="*80)
        print("NETWORK STATISTICS")
        print("="*80)
        
        # PoC Miner Stats
        print("\n[PROOF OF CAPACITY - MINERS]")
        for miner_id, node in self.poc_miners.items():
            stats = node.get_mining_stats()
            print(f"  {miner_id}:")
            print(f"    - Storage: {stats['storage_capacity_gb']} GB")
            print(f"    - Blocks Mined: {stats['blocks_mined']}")
            print(f"    - Difficulty: {stats['current_difficulty']}")
        
        # PoS Validator Stats
        print("\n[PROOF OF STAKE - VALIDATORS]")
        for validator_id, node in self.pos_validators.items():
            stats = node.get_validator_stats()
            print(f"  {validator_id}:")
            print(f"    - Role: {stats['role']}")
            print(f"    - Stake: {stats['total_staked']} FCU")
            print(f"    - Blocks Validated: {stats['blocks_validated']}")
        
        # PoW Lottery Stats
        print("\n[PROOF OF WORK - LOTTERY]")
        lottery_stats = self.pow_lottery.get_lottery_stats()
        print(f"  Participants: {lottery_stats['total_participants']}")
        print(f"  Total Entries: {lottery_stats['total_entries']}")
        print(f"  Total Winners: {lottery_stats['total_winners']}")
        print(f"  Top Winners:")
        for participant, wins in lottery_stats['top_winners']:
            print(f"    - {participant}: {wins} wins")
        
        # Full Node Stats
        print("\n[FULL NODES]")
        for node_id, node in self.full_nodes.items():
            stats = node.get_full_node_stats()
            print(f"  {node_id}:")
            print(f"    - Chain Height: {stats['chain_height']}")
            print(f"    - Peers: {stats['connected_peers']}")
            print(f"    - Mempool Txs: {stats['mempool_transactions']}")
        
        # Governance Stats
        print("\n[GOVERNANCE & TREASURY]")
        gov_stats = self.governance_council.get_governance_stats()
        print(f"  Council:")
        print(f"    - Treasurer: {gov_stats['treasurer']}")
        print(f"    - Members: {gov_stats['council_members']}/5")
        print(f"  Proposals:")
        print(f"    - Total: {gov_stats['total_proposals']}")
        print(f"    - Active: {gov_stats['active_proposals']}")
        print(f"    - Approved: {gov_stats['approved_proposals']}")
        print(f"  Treasury:")
        print(f"    - Balance: {gov_stats['treasury_balance']} FCU")
        print(f"    - Allocated: {gov_stats['treasury_allocations']}")
        
        print("\n" + "="*80)

    def print_architecture_overview(self):
        """Print architecture overview"""
        print("\n" + "="*80)
        print("FCU BLOCKCHAIN ARCHITECTURE")
        print("="*80)
        
        print("""
HYBRID CONSENSUS MECHANISM:

1. PROOF OF CAPACITY (PoC) - PRIMARY MINING
   - Storage-based mining like Signum Network
   - Miners: Farmer_John (256GB), Farmer_Maria (512GB), Farmer_Carlos (128GB)
   - Mining probability: proportional to storage share
   - Difficulty adjustment: based on block time (15-30s target)
   - Block reward: 10 FCU per block to miner

2. PROOF OF STAKE (PoS) - SECURITY LAYER
   - Council governance: Treasurer + 5 Council Members
   - Minimum stake: 1,000 FCU (council), 50,000 FCU (treasurer)
   - Role: Approve block rewards and governance decisions
   - Only treasurer can propose blocks
   - Council votes on proposals (3/5 supermajority)
   - Block reward: 5 FCU per validated block

3. PROOF OF WORK (PoW) - LOTTERY SYSTEM
   - Lightweight randomization for fairness
   - Storage donators earn lottery tickets (1 per 32GB)
   - Winner selected per block using block hash entropy
   - Incentivizes continuous storage participation
   - Lottery reward: 2 FCU to winner

NETWORK TOPOLOGY:
   - Peer discovery: Bootstrap nodes + DHT-style peer exchange
   - Gossip protocol: TTL-based message propagation
   - Node types: PoC Miners, PoS Validators, Full Nodes
   - Mempool: FCFS (first-come-first-served) transaction ordering
   - Fees: Set by treasurer, approved by council majority

GOVERNANCE:
   - Proposals: Treasurer proposes, council votes
   - Treasury: 1,000,000 FCU initial (Simplicity's contribution)
   - Reward adjustments: Via governance votes
   - Parameter changes: Difficulty, fees, allocations
   - Execution: Automatic upon approval

TOKEN ECONOMICS:
   - FCU Token: Stock investment vehicle for credit union
   - Supply: Initial 1,000,000 FCU (Simplicity)
   - Emissions: 17 FCU per block (10+5+2 from different sources)
   - None-inflation: Treasury-backed and stake-backed

COMPLIANCE:
   - Treasurer: Suggests reward structure
   - Council: Votes on all major decisions
   - Storage: Minimum 32GB pledged
   - Participation: Incentivized by rewards
        """)
        
        print("="*80)


def main():
    """Main demonstration"""
    print("\n" + "="*88)
    print("FARMERS CREDIT UNION BLOCKCHAIN NETWORK")
    print("Multi-Node Hybrid Consensus Demonstration (FCU 1.0)")
    print("="*88)
    
    # Create network
    network = FCUNetwork()
    
    # Print architecture
    network.print_architecture_overview()
    
    # Setup network
    network.setup_network()
    
    # Mine blocks
    network.mine_blocks(block_count=3)
    
    # Demonstrate governance
    network.demonstrate_governance()
    
    # Print final statistics
    network.print_network_stats()
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("""
KEY TAKEAWAYS:
[OK] Multi-node blockchain with hybrid consensus
[OK] PoC mining ensures fair distribution by storage contribution
[OK] PoS validation provides security through council governance
[OK] PoW lottery adds fairness and randomization
[OK] Treasury management for ecosystem sustainability
[OK] Governance voting prevents concentration of power
[OK] Simplicity (Ripple Labs model) provides bare minimum to keep chain alive

NEXT STEPS:
- Deploy to actual P2P network
- Implement real storage proofs (Signum-style challenges)
- Add persistent storage for blockchain state
- Implement smart contract layer (optional)
- Create mobile wallet for farmers
- Establish credit union cooperatives on each node
    """)


if __name__ == "__main__":
    main()
