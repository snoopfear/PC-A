import json
import time
from web3 import Web3

def display_logo():
    logo = """
    
   ___       __  __            _ 
  / _ \     |  \/  |          (_)
 | | | |_  _| \  / | ___   ___ _ 
 | | | \ \/ / |\/| |/ _ \ / _ \ |
 | |_| |>  <| |  | | (_) |  __/ | <3
  \___//_/\_\_|  |_|\___/ \___|_|
                              
                              
    """
    print(logo)

# Display the logo
display_logo()

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

# Load wallet information from file
with open('wallets_bull.json', 'r') as wallets_file:
    wallets = json.load(wallets_file)

def bet_bull(epoch, private_key, public_address, bet_amount_wei):
    base_fee = w3.eth.get_block('latest')['baseFeePerGas']
    max_priority_fee = w3.to_wei('2', 'gwei')
    max_fee_per_gas = base_fee + max_priority_fee
    gas_limit = 160860
    nonce = w3.eth.get_transaction_count(public_address, 'pending')
    txn = contract.functions.betBull(epoch).build_transaction({
        'chainId': 42161,
        'gas': gas_limit,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee,
        'nonce': nonce,
        'value': bet_amount_wei
    })
    signed_txn = w3.eth.account.sign_transaction(txn, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash

def claim_rewards(epoch, private_key, public_address):
    base_fee = w3.eth.get_block('latest')['baseFeePerGas']
    max_priority_fee = w3.to_wei('2', 'gwei')
    max_fee_per_gas = base_fee + max_priority_fee
    nonce = w3.eth.get_transaction_count(public_address, 'pending')
    txn = contract.functions.claim([epoch]).build_transaction({
        'chainId': 42161,
        'gas': 168860,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee,
        'nonce': nonce
    })
    signed_txn = w3.eth.account.sign_transaction(txn, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash

def has_bet(epoch, public_address):
    try:
        return contract.functions.ledger(epoch, public_address).call()[1] > 0
    except Exception as e:
        print(f"Error checking if bet is placed for epoch {epoch}: {e}")
        return False

def claim_last_5_epochs(current_epoch, private_key, public_address):
    for epoch_to_check in range(current_epoch - 5, current_epoch):
        if epoch_to_check > 0:
            if contract.functions.claimable(epoch_to_check, public_address).call():
                print(f"Claiming rewards for epoch {epoch_to_check}")
                time.sleep(60)
                claim_tx = claim_rewards(epoch_to_check, private_key, public_address)
                print(f"Claim transaction hash: {claim_tx.hex()}")

while True:
    current_epoch = contract.functions.currentEpoch().call()
    print(f"Current Epoch: {current_epoch}")

    for wallet in wallets:
        private_key = wallet['private_key']
        public_address = wallet['public_address']
        bet_amount = wallet['bet_amount']
        bet_amount_wei = w3.to_wei(bet_amount, 'ether')

        if not has_bet(current_epoch, public_address):
            account_balance = w3.eth.get_balance(public_address)
            base_fee = w3.eth.get_block('latest')['baseFeePerGas']
            max_priority_fee = w3.to_wei('2', 'gwei')
            max_fee_per_gas = base_fee + max_priority_fee
            gas_limit = 168860
            total_cost = bet_amount_wei + (gas_limit * max_fee_per_gas)
            if account_balance < total_cost:
                print(f"Insufficient funds for wallet {public_address}. Needed: {total_cost}, Available: {account_balance}")
                continue

            print(f"Placing bet for wallet {public_address}")
            bet_tx = bet_bull(current_epoch, private_key, public_address, bet_amount_wei)
            print(f"Bet transaction hash: {bet_tx.hex()}")

        # Check and claim rewards for the last 5 epochs
        claim_last_5_epochs(current_epoch, private_key, public_address)

    # Wait a short period before checking again
    time.sleep(20)  # Adjust the sleep time as needed for your use case
