#!/usr/bin/env python3
"""
FCU BLOCKCHAIN - QUICK START GUIDE
Farmers Credit Union Multi-Node Hybrid Consensus Blockchain
"""

import sys
import time
from pathlib import Path

# Add FCU blockchain to path
fcu_path = Path(__file__).parent
sys.path.insert(0, str(fcu_path))

from core import Blockchain, Transaction, TransactionType
from consensus import PoCMiner, PoSValidator, PoWLottery
from node import PoCMinerNode, PoSValidatorNode, FullNode
from governance import GovernanceCouncil, ProposalType
from network import PeerInfo


def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"{title.center(80)}")
    print(f"{'='*80}\n")


def example_1_basic_blockchain():
    """Example 1: Basic Blockchain Setup"""
    print_header("Example 1: Creating a Simple FCU Blockchain")
    
    # Create blockchain
    blockchain = Blockchain(chain_id="FCU_EXAMPLE_1")
    print(f"[*] Created blockchain: {blockchain.chain_id}")
    print(f"[*] Chain length: {blockchain.get_chain_length()}")
    print(f"[*] Genesis block hash: {blockchain.chain[0].hash[:16]}...")
    
    # Check initial Simcoin donation to FCU
    sim_balance = blockchain.get_balance("FCU_TREASURY")
    print(f"[*] FCU treasury balance (Simcoin): {sim_balance} FCU")
    
    return blockchain


def example_2_poc_mining():
    """Example 2: Proof of Capacity Mining"""
    print_header("Example 2: Setting Up PoC Miners")
    
    # Create miners with different storage capacities
    farmers = [
        ("Farmer_Alice", 256.0),   # 256 GB
        ("Farmer_Bob", 512.0),     # 512 GB
        ("Farmer_Charlie", 128.0), # 128 GB
    ]
    
    print("[*] Creating storage donators:")
    miners = {}
    total_capacity = 0
    
    for farmer_id, storage_gb in farmers:
        miner = PoCMiner(farmer_id, storage_gb)
        miners[farmer_id] = miner
        total_capacity += storage_gb
        
        prob = miner.get_mining_probability(total_capacity)
        print(f"    {farmer_id}: {storage_gb} GB (mining prob: {prob*100:.1f}%)")
    
    # Simulate mining attempt
    print("\n[*] Simulating PoC mining...")
    farmer_id = "Farmer_Alice"
    miner = miners[farmer_id]
    
    previous_hash = "genesis_hash_0000"
    nonce, time_taken = miner.mine_block(
        previous_hash=previous_hash,
        difficulty=2,  # Lower difficulty for demo
        timeout=5.0
    )
    
    if nonce is not None:
        print(f"    [MINED] {farmer_id} found nonce: {nonce}")
        print(f"    [TIME] Mining took: {time_taken:.3f} seconds")
        print(f"    [REWARD] {farmer_id} receives: 10 FCU")
    else:
        print(f"    [TIMEOUT] Mining took too long")


def example_3_pos_governance():
    """Example 3: Proof of Stake Governance"""
    print_header("Example 3: Setting Up PoS Council Governance")
    
    # Create treasurer
    treasurer = PoSValidator(
        validator_id="TREASURER_Alice",
        role=PoSValidator.ROLE_TREASURER,
        min_stake=50000.0
    )
    treasurer.total_staked = 50000.0
    print(f"[*] Treasurer: {treasurer.validator_id} ({treasurer.total_staked} FCU stake)")
    
    # Create council members
    council = {}
    council_members = ["Bob", "Charlie", "Diana", "Eve", "Frank"]
    
    print("[*] Creating council members:")
    for name in council_members:
        validator = PoSValidator(
            validator_id=f"COUNCIL_{name}",
            role=PoSValidator.ROLE_COUNCIL,
            min_stake=10000.0
        )
        validator.total_staked = 10000.0
        council[f"COUNCIL_{name}"] = validator
        print(f"    COUNCIL_{name}: {validator.total_staked} FCU stake")
    
    # Create governance council
    governance = GovernanceCouncil(
        treasurer_id="TREASURER_Alice",
        council_members=list(council.keys())
    )
    
    print(f"\n[*] Council created with {len(council)} members")
    print(f"[*] Treasury balance: {governance.treasury.get_balance()} FCU")
    
    return governance, council


def example_4_voting():
    """Example 4: Council Voting on Proposal"""
    print_header("Example 4: Council Voting on Proposal")
    
    # Create governance
    governance, council = example_3_pos_governance()
    
    # Create and vote on proposal
    print("\n[*] Treasurer proposes: Increase miner rewards")
    proposal_id = governance.create_proposal(
        proposal_type=ProposalType.REWARD_ADJUSTMENT,
        description="Increase PoC miner reward from 10 to 12 FCU",
        proposed_changes={'poc_miner_reward': 12.0}
    )
    print(f"    Proposal ID: {proposal_id}")
    
    # Simulate voting
    print("\n[*] Council voting:")
    votes = {
        "COUNCIL_Bob": True,
        "COUNCIL_Charlie": True,
        "COUNCIL_Diana": True,
        "COUNCIL_Eve": False,
        "COUNCIL_Frank": True,
    }
    
    for voter, vote in votes.items():
        governance.vote_on_proposal(proposal_id, voter, vote)
        vote_text = "[YES]" if vote else "[NO]"
        print(f"    {voter}: {vote_text}")
    
    # Check result
    yes, no, total = governance.count_votes(proposal_id)
    print(f"\n[*] Results: {yes} YES, {no} NO")
    
    if governance.proposals[proposal_id].is_approved():
        print(f"[APPROVED] Proposal will be executed!")
        new_reward = governance.reward_config.poc_miner_reward
        print(f"    New miner reward: {new_reward} FCU")


def example_5_lottery():
    """Example 5: PoW Lottery System"""
    print_header("Example 5: Proof of Work Lottery for Storage Donators")
    
    # Create lottery
    lottery = PoWLottery(block_time=22)
    
    # Register participants
    participants = [
        ("Farmer_John", 256.0),
        ("Farmer_Maria", 512.0),
        ("Farmer_Carlos", 128.0),
    ]
    
    print("[*] Registering lottery participants:")
    for farmer_id, storage_gb in participants:
        lottery.register_participant(farmer_id, storage_gb)
        tickets = max(1, int(storage_gb / 32.0))
        print(f"    {farmer_id}: {storage_gb} GB → {tickets} tickets per block")
    
    # Simulate lottery
    print("\n[*] Simulating lottery for 5 blocks:")
    for block_num in range(5):
        block_hash = f"block_{block_num}"
        winner = lottery.select_winner(block_hash, block_num)
        lottery.add_lottery_ticket("Farmer_John", block_num)
        lottery.add_lottery_ticket("Farmer_Maria", block_num)
        lottery.add_lottery_ticket("Farmer_Carlos", block_num)
        print(f"    Block {block_num}: Winner = {winner} [+2 FCU]")
    
    # Statistics
    stats = lottery.get_lottery_stats()
    print(f"\n[*] Lottery Statistics:")
    print(f"    Total participants: {stats['total_participants']}")
    print(f"    Total lottery entries: {stats['total_entries']}")
    print(f"    Top winners:")
    for participant, wins in stats['top_winners']:
        print(f"      - {participant}: {wins} wins")


def example_6_multi_node_network():
    """Example 6: Multi-Node Network Setup"""
    print_header("Example 6: Setting Up Multi-Node Network")
    
    # Create different node types
    nodes = {}
    
    # PoC Miners
    print("[*] Creating PoC Miner Nodes:")
    miner1 = PoCMinerNode("Farmer_Alice_Node", storage_gb=256, port=8010)
    miner2 = PoCMinerNode("Farmer_Bob_Node", storage_gb=512, port=8011)
    nodes["Miner1"] = miner1
    nodes["Miner2"] = miner2
    print(f"    {miner1.node_id}: PoC Miner (256 GB)")
    print(f"    {miner2.node_id}: PoC Miner (512 GB)")
    
    # PoS Validators
    print("\n[*] Creating PoS Validator Nodes:")
    validator1 = PoSValidatorNode(
        "Treasurer_Alice",
        role=PoSValidator.ROLE_TREASURER,
        initial_stake=50000.0,
        port=8020
    )
    validator2 = PoSValidatorNode(
        "Council_Bob",
        role=PoSValidator.ROLE_COUNCIL,
        initial_stake=10000.0,
        port=8021
    )
    nodes["Validator1"] = validator1
    nodes["Validator2"] = validator2
    print(f"    {validator1.node_id}: Treasurer (50,000 FCU stake)")
    print(f"    {validator2.node_id}: Council member (10,000 FCU stake)")
    
    # Full Nodes
    print("\n[*] Creating Full Nodes:")
    full1 = FullNode("FullNode_1", port=8030)
    full2 = FullNode("FullNode_2", port=8031)
    nodes["Full1"] = full1
    nodes["Full2"] = full2
    print(f"    {full1.node_id}: Full Node")
    print(f"    {full2.node_id}: Full Node")
    
    # Connect nodes
    print("\n[*] Establishing peer connections (mesh topology):")
    all_nodes = list(nodes.values())
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
        print(f"    {node.node_id}: connected to {node.peer_discovery.get_peer_count()} peers")


def example_7_full_demo():
    """Example 7: Full Network Demo"""
    print_header("Example 7: Running Complete Network Demo")
    
    print("[*] This is the comprehensive demonstration")
    print("[*] Run: python main.py")
    print("\nThe main.py script demonstrates:")
    print("  1. Network setup with all node types")
    print("  2. 3 blocks of mining simulation")
    print("  3. PoS council voting on proposals")
    print("  4. Comprehensive network statistics")


def main():
    """Run all examples"""
    print("""
    
╔════════════════════════════════════════════════════════════════════════════╗
║           FARMERS CREDIT UNION BLOCKCHAIN - QUICK START GUIDE             ║
║              Multi-Node Hybrid Consensus Implementation                    ║
║                                                                            ║
║            Visit README.md for comprehensive documentation                ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    print("Running 7 examples demonstrating FCU Blockchain features...\n")
    
    try:
        # Example 1: Basic Blockchain
        example_1_basic_blockchain()
        input("\nPress Enter to continue to Example 2...")
        
        # Example 2: PoC Mining
        example_2_poc_mining()
        input("\nPress Enter to continue to Example 3...")
        
        # Example 3: PoS Governance
        example_3_pos_governance()
        input("\nPress Enter to continue to Example 4...")
        
        # Example 4: Voting
        example_4_voting()
        input("\nPress Enter to continue to Example 5...")
        
        # Example 5: Lottery
        example_5_lottery()
        input("\nPress Enter to continue to Example 6...")
        
        # Example 6: Multi-Node Network
        example_6_multi_node_network()
        input("\nPress Enter to continue to Example 7...")
        
        # Example 7: Full Demo
        example_7_full_demo()
        
        # Summary
        print_header("Quick Start Complete!")
        print("""
[*] FCU Blockchain has been successfully demonstrated!

KEY CONCEPTS COVERED:
  ✓ Blockchain creation and genesis block
  ✓ Proof of Capacity mining with storage
  ✓ Proof of Stake governance with council voting
  ✓ Proof of Work lottery for fairness
  ✓ Multi-node P2P network setup
  ✓ Treasury management and proposals

NEXT STEPS:
  1. Review README.md for detailed documentation
  2. Explore core.py, consensus.py, and governance.py
  3. Modify main.py to create custom network topologies
  4. Test with different parameter configurations
  5. Deploy to testnet (coming soon)

USAGE PATTERNS:

  # Create blockchain
  blockchain = Blockchain("FCU_MAINNET")
  
  # Create miners
  miner = PoCMinerNode("Farmer_1", storage_gb=256)
  
  # Setup governance
  governance = GovernanceCouncil("Treasurer_Alice", council_members)
  
  # Create proposals
  governance.create_proposal(ProposalType.REWARD_ADJUSTMENT, ...)
  
  # Run demo
  python main.py

SUPPORT:
  - Documentation: README.md
  - Examples: This file (quickstart.py)
  - Full Demo: main.py
  - Architecture: core.py, consensus.py, governance.py, network.py

Happy Farming on the FCU Blockchain! 🌾
        """)
        
    except KeyboardInterrupt:
        print("\n\n[*] Quick start interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
