import json
import time
import random
import logging
from web3 import Web3

# Load contract ABI from a JSON file
with open('ContractABI.json', 'r') as abi_file:
    abi_content = json.load(abi_file)
    if isinstance(abi_content, dict) and 'result' in abi_content:
        contract_abi = json.loads(abi_content['result'])
    else:
        contract_abi = abi_content

# Connect to Arbitrum network (replace with your provider)
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))

# Check if connected to the network
if not w3.is_connected():
    print("Failed to connect to the network")
    exit()

# Contract address (convert to checksum address)
contract_address = Web3.to_checksum_address('0x1cdc19b13729f16c5284a0ace825f83fc9d799f4')

# Initialize contract
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

def bet_bull(private_key, public_address, epoch, bet_amount_wei, nonce):
    try:
        base_fee = w3.eth.get_block('latest')['baseFeePerGas']
        max_priority_fee = w3.to_wei('2', 'gwei')
        max_fee_per_gas = base_fee + max_priority_fee
        gas_limit = 160860
        txn = contract.functions.betBull(epoch).build_transaction({
            'chainId': 42161,  # Arbitrum mainnet chain ID
            'gas': gas_limit,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee,
            'nonce': nonce,
            'value': bet_amount_wei
        })
        signed_txn = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash
    except Exception as e:
        logging.error(f"Error sending bet transaction: {e}")
        return None

def claim_rewards(private_key, public_address, epoch, nonce):
    try:
        base_fee = w3.eth.get_block('latest')['baseFeePerGas']
        max_priority_fee = w3.to_wei('2', 'gwei')
        max_fee_per_gas = base_fee + max_priority_fee
        txn = contract.functions.claim([epoch]).build_transaction({
            'chainId': 42161,  # Arbitrum mainnet chain ID
            'gas': 168860,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee,
            'nonce': nonce
        })
        signed_txn = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash
    except Exception as e:
        logging.error(f"Error sending claim transaction: {e}")
        return None

def has_bet(public_address, epoch):
    try:
        return contract.functions.ledger(epoch, public_address).call()[1] > 0
    except Exception as e:
        logging.error(f"Error checking if bet is placed for epoch {epoch}: {e}")
        return False

def has_bet_bear(public_address, epoch):
    try:
        bet_info = contract.functions.ledger(epoch, public_address).call()
        return bet_info[1] > 0
    except Exception as e:
        logging.error(f"Error checking if betBear is placed for epoch {epoch}: {e}")
        return False

def claim_last_5_epochs(private_key, public_address, current_epoch, nonce):
    for epoch_to_check in range(current_epoch - 5, current_epoch):
        if epoch_to_check > 0:
            try:
                if contract.functions.claimable(epoch_to_check, public_address).call():
                    print(f"Claiming rewards for epoch {epoch_to_check}")
                    time.sleep(60)  # Delay for 1 minute before claiming rewards
                    claim_tx = claim_rewards(private_key, public_address, epoch_to_check, nonce)
                    if claim_tx:
                        print(f"Claim transaction hash: {claim_tx.hex()}")
            except Exception as e:
                logging.error(f"Error claiming rewards for epoch {epoch_to_check}: {e}")

# Set up logging
logging.basicConfig(filename='script.log', level=logging.ERROR)

# Load wallets from file
wallets = []
with open('wallets_bull.txt', 'r') as file:
    for line in file:
        private_key, public_address = line.strip().split()
        wallets.append((private_key, public_address))

# Define range for bet amount (in ETH)
bet_amount_range = (0.00049, 0.00051)  # Example: between 0.01 and 0.1 ETH

for private_key, public_address in wallets:
    # Initialize nonce
    nonce = w3.eth.get_transaction_count(public_address, 'pending')

    current_epoch = contract.functions.currentEpoch().call()
    claim_last_5_epochs(private_key, public_address, current_epoch, nonce)

    previous_epoch = current_epoch
    bet_placed_epoch = None

    print(f"Starting script for {public_address}. Initial Epoch: {previous_epoch}")

    try:
        while True:
            current_epoch = contract.functions.currentEpoch().call()

            if current_epoch > previous_epoch:
                print(f"Current Epoch: {current_epoch}")
                previous_epoch = current_epoch
                bet_placed_epoch = None

            if bet_placed_epoch != current_epoch and not has_bet(public_address, current_epoch) and not has_bet_bear(public_address, current_epoch):
                account_balance = w3.eth.get_balance(public_address)
                base_fee = w3.eth.get_block('latest')['baseFeePerGas']
                max_priority_fee = w3.to_wei('2', 'gwei')
                max_fee_per_gas = base_fee + max_priority_fee
                gas_limit = 168860

                # Randomly choose a bet amount within the specified range for each bet
                bet_amount = random.uniform(*bet_amount_range)
                bet_amount_wei = w3.to_wei(bet_amount, 'ether')
                total_cost = bet_amount_wei + (gas_limit * max_fee_per_gas)

                if account_balance < total_cost:
                    print(f"Insufficient funds to place bet on epoch {current_epoch}. Needed: {total_cost}, Available: {account_balance}")
                    break

                print(f"Placing bet on epoch {current_epoch} for {public_address} with amount {bet_amount} ETH")
                bet_tx = bet_bull(private_key, public_address, current_epoch, bet_amount_wei, nonce)
                if bet_tx:
                    print(f"Bet transaction hash: {bet_tx.hex()}")
                    nonce += 1  # Increment nonce after sending the transaction
                    bet_placed_epoch = current_epoch

            else:
                print(f"Already placed a bet on epoch {current_epoch}")

            claim_last_5_epochs(private_key, public_address, current_epoch, nonce)
            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\nScript interrupted by user for {public_address}. Exiting gracefully...")
