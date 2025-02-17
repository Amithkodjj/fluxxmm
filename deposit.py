import aiohttp
from config import OXAPAY_API_KEY, WEBHOOK_URL
from utils import generate_order_id

async def create_invoice(amount, deal_id):
    url = "https://api.oxapay.com/merchants/request"
    headers = {
        "Authorization": f"Bearer {OXAPAY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "merchant": OXAPAY_API_KEY,
        "amount": amount,
        "orderId": deal_id,
        "callbackUrl": f"{WEBHOOK_URL}/oxapay_callback",
        "feePaidByPayer": 1,
        "lifeTime": 60,
        'description': "Deposit to escrow wallet",
        'isTest': False,
        'isMiniApp': True
    }
    
    print(f"Creating invoice with payload: {payload}")  # Log the payload

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            print(f"OxaPay Response: {result}")  # Log the response
            return result

async def handle_deposit(update, context):
    amount = context.user_data.get("amount")
    if not amount:
        await update.message.reply_text("Please set the deposit amount first.")
        return

    invoice = await create_invoice(amount)
    if invoice.get("status") == "success":
        payment_url = invoice["data"]["payLink"]
        await update.message.reply_text(
            f"Please complete your deposit of {amount} USDT using this link:\n{payment_url}"
        )
        context.user_data["order_id"] = invoice["data"]["order_id"]
    else:
        await update.message.reply_text("Sorry, there was an error creating the invoice. Please try again later.")

# Implement other deposit-related functions

