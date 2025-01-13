import asyncio
import os
from dotenv import load_dotenv
from src.integrations.helius import HeliusAPI

async def test_helius():
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize Helius API
        helius = HeliusAPI()
        
        # Test with known Solana tokens
        usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        pump_program = os.getenv("PUMP_FUN_PROGRAM_ID", "PFv6UgNmGt3tECGZ8HyLTHx5fXgZCq5tYuqEyJmTXgw")
        
        print("Testing Helius API connection...")
        
        print("\n1. Testing Token Metadata:")
        metadata = await helius.get_token_metadata(usdc_address)
        print(f"USDC Metadata: {metadata}")
        
        print("\n2. Testing Token Supply:")
        supply = await helius.get_token_supply(usdc_address)
        print(f"USDC Supply Info: {supply}")
        
        print("\n3. Testing Program Transactions:")
        transactions = await helius.get_program_transactions(pump_program, days=1)
        print(f"Found {len(transactions)} recent transactions for pump.fun")
        if transactions:
            print(f"Latest transaction: {transactions[0]}")
            
        print("\n4. Testing Token Transfers:")
        transfers = await helius.get_token_transfers(usdc_address)
        print(f"Found {len(transfers)} recent USDC transfers")
        if transfers:
            print(f"Latest transfer: {transfers[0]}")
            
        print("\nAPI connection and endpoints working successfully!")
        
    except Exception as e:
        print(f"\nError testing Helius API: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_helius())
