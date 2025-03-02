import asyncio
import os
import hmac
import hashlib
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import TOKEN, OXAPAY_API_KEY, ADMIN_ID
from handlers import *
from deposit import handle_deposit
from telegram.error import BadRequest
from refund import handle_refund, handle_refund_agreement
from utils import get_active_deal, update_active_deal, remove_active_deal
from datetime import datetime, timedelta
import httpx
import time
from fastapi.responses import PlainTextResponse
from login import *

app = FastAPI()

# Initialize bot
bot = Application.builder().token(TOKEN).build().bot

DEAL_TYPE_DISPLAY = {
    'b_and_s': 'Buy and Sell',
    'p2p': 'P2P Transfer'
}

async def error_handler(update, context):
    print(f"Error occurred: {context.error}")

async def run_bot():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("startdeal", handle_startdeal))
    application.add_handler(CommandHandler("p2pfee", handle_p2pfee))
    application.add_handler(CommandHandler("bsfee", handle_bsfee))
    application.add_handler(CommandHandler("trades", handle_trades))
    application.add_handler(CommandHandler("killdeal", handle_killdeal))
    application.add_handler(CommandHandler("killall", handle_killall))
    application.add_handler(CommandHandler("setsticker", handle_setsticker))
    application.add_handler(CommandHandler("getdeal", handle_getdeal))
    application.add_handler(CommandHandler("refund", handle_refund))
    application.add_handler(CommandHandler("form", handle_form))
    application.add_handler(CommandHandler("login", handle_login))
    application.add_handler(CommandHandler("logout", handle_logout))
    application.add_handler(CommandHandler("setfee", handle_setfee))
    


    application.add_handler(CallbackQueryHandler(handle_refund_agreement, pattern="^refund_(agree|deny)$"))
    application.add_handler(CallbackQueryHandler(handle_callback))  

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_form))
    application.add_error_handler(error_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_bot())

@app.get("/")
async def home():
    return {"message": "Welcome to the FastAPI App!"}

@app.get("/ping", response_class=PlainTextResponse)
async def ping():
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/get")
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000)
    return f"PONG {response_time}ms"
@app.get("/webhook")
async def webhook():
    return {"message": "Webhook is working!"}

@app.post("/oxapay_callback")
async def oxapay_callback(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.body()
        signature = request.headers.get('sign')
        
        if signature:
            calculated_signature = hmac.new(
                OXAPAY_API_KEY.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            if signature != calculated_signature:
                raise HTTPException(status_code=400, detail="Invalid signature")

        data = await request.json()
        print(f"Callback Data Received: {data}")

        deal_id = data.get("orderId")
        if not deal_id:
            raise HTTPException(status_code=400, detail="Missing orderId")

        deal_data = get_active_deal(deal_id)
        if not deal_data:
            print(f"No active deal found for deal_id: {deal_id}")
            return {"message": "No active deal found"}
        
        group_id = deal_data['group_id']

        buyer = await bot.get_chat(deal_data['buyer'])
        seller = await bot.get_chat(deal_data['seller'])

        status = data.get("status")
        if status == "Waiting":
            await bot.send_message(
                chat_id=group_id,
                text=f"💳 Payment initiated by <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\nWaiting for deposit...",
                parse_mode='HTML'
            )
        elif status == "Confirming":
            await bot.send_message(
                chat_id=group_id,
                text=f"🔄 Payment is being confirmed for <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>",
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
            
            amount = deal_data['amount']
            fee = calculate_fee(amount, deal_data['deal_type'])
            total = amount + fee

            keyboard = [  
                [InlineKeyboardButton("💰 Release Payment", callback_data="release_payment")],  
                [InlineKeyboardButton("⏳ Check Timer", callback_data="check_timer")],  
                [InlineKeyboardButton("👨‍💼 Involve Moderator", callback_data="mod")],  
                [InlineKeyboardButton("🚫 End Deal", callback_data="back")]  
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_message = await bot.send_message(
                chat_id=group_id,
                text=(
                    f"<b>⚠️ FLUXX ESCROW BOT - PAYMENT CONFIRMED ✅</b>\n\n"
                    f"💵 <b>Deposit Amount:</b> ${amount:.2f}\n"
                    f"✅ <b>Payment confirmed from:</b> <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
                    f"🔄 <b>Escrow Fee:</b> ${fee:.2f}\n"
                    f"💰 <b>Total Amount:</b> ${total:.2f}\n\n"
                    f"<b>⚠️ IMPORTANT INSTRUCTIONS:</b>\n"
                    f"1. Ensure the transaction is fully completed before proceeding.\n"
                    f"2. <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a> Verify that all items/services meet your expectations.\n"
                    f"3. <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a> Only click 'Release Payment' if fully satisfied with the transaction.\n"
                    f"4. If you encounter any issues, click 'Involve Moderator' immediately.\n\n"
                    f"<b>🚫 Do NOT release payment before deal completion to avoid disputes.</b>\n"
                    f"❗ All disputes or suspected scams will be investigated thoroughly.\n\n"
                    f"<b>👥 Participants:</b>\n"
                    f"🔹 <b>Buyer:</b> <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
                    f"🔹 <b>Seller:</b> <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>\n"
                    f"<b>⏱ Time Remaining to Complete Trade: 60:00 Minutes</b> \n"
                    f"⚠️ <i>Please complete the trade before the timer expires, or a moderator will be involved automatically.</i>"
                ),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            background_tasks.add_task(check_payment_timeout, bot, group_id, deal_id, sent_message.message_id)
        elif status == "Expired":
            await bot.send_message(
                chat_id=group_id,
                text=f"⚠️ Payment time expired for <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>",
                parse_mode='HTML'
            )
            remove_active_deal(deal_id)

    except Exception as e:
        print(f"Error in callback: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"message": "ok"}

@app.post("/withdraw")
async def withdraw_callback(request: Request):
    try:
        data = await request.json()
        print(f"Withdrawal Callback Data Received: {data}")

        description = data.get("description", "")
        seller_id = description.split()[-1]

        status = data.get("status")
        amount = data.get("amount")
        currency = data.get("currency")

        await send_withdrawal_update_to_seller(bot, seller_id, status, amount, currency)

    except Exception as e:
        print(f"Error in withdrawal callback: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"message": "ok"}

async def check_payment_timeout(bot, group_id, deal_id, message_id):
    await asyncio.sleep(3600)  # 60 minutes in seconds
    
    deal_data = get_active_deal(deal_id)
    if not deal_data or deal_data['status'] != 'deposited':
        return
        
    buyer = await bot.get_chat(deal_data['buyer'])
    seller = await bot.get_chat(deal_data['seller'])
    
    group_alert = (
        "⚠️ <b>Payment Release Timeout</b>\n\n"
        "60 minutes have passed without payment release.\n"
        "A moderator has been automatically involved to assist.\n\n"
        f"Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
        f"Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>"
    )
    
    await bot.send_message(
        chat_id=group_id,
        text=group_alert,
        parse_mode='HTML'
    )
    
    mod_alert = (
        "<b>⚠️ Payment Release Timeout Alert</b>\n\n"
        f"Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
        f"Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>\n"
        f"Amount: ${deal_data['amount']:.2f}\n"
        f"Deal Type: {DEAL_TYPE_DISPLAY.get(deal_data['deal_type'], deal_data['deal_type'])}\n\n"
        f"<a href='https://t.me/c/{str(group_id)[4:]}/{message_id}'>View Deal Message</a>\n\n"
        "Please review this case immediately."
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=mod_alert,
        parse_mode='HTML'
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

