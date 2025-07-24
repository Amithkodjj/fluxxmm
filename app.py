from quart import Quart, request
from config import OXAPAY_API_KEY, ADMIN_ID, TOKEN
import hmac
import hashlib
from utils import *
from handlers import send_withdrawal_update_to_seller
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes, ApplicationBuilder
from config import TOKEN
from datetime import datetime, timedelta
import asyncio

DEAL_TYPE_DISPLAY = {
    'b_and_s': 'Buy and Sell',
    'p2p': 'P2P Transfer'
}

# Initialize bot
bot = Application.builder().token(TOKEN).build().bot

app = Quart(__name__)

@app.route('/')
async def home():
    return "Welcome to the Quart App!"

@app.route("/webhook", methods=["GET"])
async def webhook():
    return "Webhook is working!"

@app.route("/oxapay_callback", methods=["POST"])
async def oxapay_callback():
    try:
        if not request.headers.get('sign'):
            print("No signature provided - processing callback anyway")
            data = await request.get_json()
        else:
            signature = request.headers.get('sign')
            payload = await request.get_data()
            calculated_signature = hmac.new(
                OXAPAY_API_KEY.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            if signature != calculated_signature:
                print("Invalid signature detected")
                return "Invalid signature", 400

            print("Signature verified")
            data = await request.get_json()
        print(f"Callback Data Received: {data}")

        deal_id = data.get("orderId")
        if not deal_id:
            return "Missing orderId", 400

        group_id = deal_id.split("None")[-1][:14]  

        deal_data = get_active_deal(deal_id)
        if not deal_data:
            print(f"No active deal found for deal_id: {deal_id}")
            return "", 200

        buyer = await bot.get_chat(deal_data['buyer'])
        seller = await bot.get_chat(deal_data['seller'])

        status = data.get("status")
        if status == "Waiting":
            await bot.send_message(
                chat_id=group_id,
                text="""<blockquote>💳 <b>Payment Initiated</b>
                
Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>
Status: Awaiting deposit confirmation</blockquote>""",
                parse_mode='HTML'
            )

        elif status == "Confirming":
            await bot.send_message(
                chat_id=group_id,
                text="""<blockquote>🔄 <b>Payment Confirmation in Progress</b>

Transaction is being verified by the payment network
Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a></blockquote>""",
                parse_mode='HTML'
            )

        elif status == "Paid":
            update_active_deal(deal_id, {
                'status': 'deposited',
                'payment_time': datetime.now().isoformat()
            })
            try:
                await bot.delete_message(
                    chat_id=group_id,
                    message_id=data.get("message_id")  
                )
            except:
                pass
            
            from handlers import calculate_fee
            amount = deal_data['amount']
            fee = calculate_fee(amount, deal_data['deal_type'])
            total = amount + fee

            keyboard = [  
                [InlineKeyboardButton("💰 Release Payment", callback_data="release_payment")],  
                [InlineKeyboardButton("⏳ Check Timer", callback_data="check_timer")],  
                [InlineKeyboardButton("🛡 Involve Moderator", callback_data="mod")],  
                [InlineKeyboardButton("❌ Cancel Deal", callback_data="back")]  
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_message = await bot.send_message(
                chat_id=group_id,
                text=f"""<blockquote>🛡 <b>Escrow Payment Confirmed</b> ✅

<b>Transaction Details</b>
▸ Amount: ${amount:.2f}
▸ Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>
▸ Service Fee: ${fee:.2f}
▸ Total: ${total:.2f}

<b>Important Instructions</b>
1. Complete all transaction requirements before releasing funds
2. Buyer must verify goods/services before payment release
3. Contact moderator immediately for any disputes

<b>Participants</b>
▸ Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>
▸ Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>

⏱ <b>Time Remaining:</b> 60:00 minutes
⚠️ Moderator will auto-intervene if timer expires</blockquote>""",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            asyncio.create_task(check_payment_timeout(bot, group_id, deal_id, sent_message.message_id))
            
        elif status == "Expired":
            await bot.send_message(
                chat_id=group_id,
                text=f"""<blockquote>⚠️ <b>Payment Expired</b>

The payment window has closed for this transaction
Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a></blockquote>""",
                parse_mode='HTML'
            )
            remove_active_deal(deal_id)

    except Exception as e:
        print(f"Error in callback: {e}")
        return "Internal Server Error", 500

    return "ok", 200

@app.route("/withdraw", methods=["POST"])
async def withdraw_callback():
    try:
        data = await request.get_json()
        print(f"Withdrawal Callback Data Received: {data}")

        description = data.get("description", "")
        seller_id = description.split()[-1]

        status = data.get("status")
        amount = data.get("amount")
        currency = data.get("currency")

        await send_withdrawal_update_to_seller(bot, seller_id, status, amount, currency)

    except Exception as e:
        print(f"Error in withdrawal callback: {e}")
        return "Internal Server Error", 500

    return "ok", 200

async def check_payment_timeout(bot, group_id, deal_id, message_id):
    await asyncio.sleep(3600)
    
    deal_data = get_active_deal(deal_id)
    if not deal_data or deal_data['status'] != 'deposited':
        return
        
    buyer = await bot.get_chat(deal_data['buyer'])
    seller = await bot.get_chat(deal_data['seller'])
    
    await bot.send_message(
        chat_id=group_id,
        text="""<blockquote>⚠️ <b>Payment Release Timeout</b>

60 minutes have passed without payment release
A moderator has been automatically notified

<b>Participants</b>
▸ Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>
▸ Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a></blockquote>""",
        parse_mode='HTML'
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"""<blockquote>🛑 <b>Moderator Alert: Payment Timeout</b>

<b>Transaction Details</b>
▸ Amount: ${deal_data['amount']:.2f}
▸ Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>
▸ Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>
▸ Deal Type: {DEAL_TYPE_DISPLAY.get(deal_data['deal_type'], deal_data['deal_type'])}

<a href='https://t.me/c/{str(group_id)[4:]}/{message_id}'>View Transaction</a>

Please review this case immediately</blockquote>""",
        parse_mode='HTML'
    )
