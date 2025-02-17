import aiohttp
from config import *
from utils import *
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from remarks import ReviewSystem

review_system = ReviewSystem()

WITHDRAWAL_FEES = {
    "LTC": 0.12,
    "ETH": 2.18,
    "DOGE": 0.16,
    "USDT": 0.28,
    "TON": 0.16,
    "POL": 0.16,
    "TRX": 0.28,
    'SOL': 0.40,
    "BTC": 2.89
}

network_mapping = {
        "BTC": ("BTC", 'Bitcoin'),
        "LTC": ("LTC", "litecoin"),
        "ETH": ("ETH", "ERC20"),
        "DOGE": ("DOGE", "dogecoin"),
        "USDT_BEP20": ("USDT", "BEP20"),
        "USDT_TON": ("USDT", "TON"),
        "TON": ("TON", "ton"),
        "POL": ("POL", "polygon"),
        "TRX": ("TRX", "TRC20"),
        "SOL": ("SOL", "solana")
    }

kbd = [
        [InlineKeyboardButton("Bitcoin", callback_data="coin_BTC"),
         InlineKeyboardButton("Ethereum", callback_data="coin_ETH")],
        [InlineKeyboardButton("TON", callback_data="coin_TON"),
         InlineKeyboardButton("SOL", callback_data="coin_SOL"),
         InlineKeyboardButton("LTC", callback_data="coin_LTC")],
        [InlineKeyboardButton("USDT (TON)", callback_data="coin_USDT_TON"),
         InlineKeyboardButton("USDT (BEP20)", callback_data="coin_USDT_BEP20")],
         [InlineKeyboardButton("POL", callback_data="coin_POL"),
        InlineKeyboardButton("DOGE", callback_data="coin_DOGE")]
    ]
async def create_payout(amount, address, currency, network, seller_id, memo=None):
    url = "https://api.oxapay.com/api/send"
    headers = {
        "Authorization": f"Bearer {OXAPAY_PAYOUT_KEY}",
        "Content-Type": "application/json"
    }
    if network.upper() == "TON" and currency == "USDT":
        network = "Ton"

    payload = {
        "key": OXAPAY_PAYOUT_KEY,
        "amount": str(amount),
        "currency": currency,
        "network": network.lower(),
        "address": address,
        "description": f"Withdrawal to {seller_id}",
        "callbackUrl": f"{WEBHOOK_URL}/withdraw"
    }
    if memo:
        payload["memo"] = memo

    print(f"Payout Request Data: {payload}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            return await response.json()

async def handle_release_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id

    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            break

    if not deal_id:
        await query.edit_message_text("No active deal found for this group.")
        return

    deal_data = get_active_deal(deal_id)
    if not deal_data:
        await query.edit_message_text("Error: Deal data not found.")
        return

    if query.from_user.id == deal_data['seller']:
        await query.answer("Sellers cannot release the payment ❌", show_alert=True)
        return

    # Then check if user is buyer or admin
    if query.from_user.id != deal_data['buyer'] and str(query.from_user.id) != ADMIN_ID:
        await query.answer("Only the buyer or admin can release the payment ❌", show_alert=True)
        return

    if deal_data.get('refund_status') == 'initiated':
        await query.answer("Refund is in process on this deal", show_alert=True)
        return
        
    if deal_data.get('refund_status') == 'completed':
        await query.edit_message_text("This deal was ended due to buyer getting refunded")
        return
        
    if deal_data.get('status') == 'completed':
        await query.edit_message_text("This deal has ended")
        return
    
    if deal_data.get('status') == 'released':
        await query.answer("Payment release button has been clicked ⚠", show_alert=True)
        return

    
    deal_data['status'] = 'released'
    update_active_deal(deal_id, {'status': 'released'})
    
    seller = await context.bot.get_chat(deal_data['seller'])
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data="coin_BTC"),
         InlineKeyboardButton("Ethereum", callback_data="coin_ETH")],
        [InlineKeyboardButton("TON", callback_data="coin_TON"),
         InlineKeyboardButton("SOL", callback_data="coin_SOL"),
         InlineKeyboardButton("LTC", callback_data="coin_LTC")],
        [InlineKeyboardButton("USDT (TON)", callback_data="coin_USDT_TON"),
         InlineKeyboardButton("USDT (BEP20)", callback_data="coin_USDT_BEP20")],
         [InlineKeyboardButton("POL", callback_data="coin_POL"),
        InlineKeyboardButton("DOGE", callback_data="coin_DOGE")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    seller_link = f'<a href="tg://user?id={seller.id}">{seller.first_name}</a>'
    await query.edit_message_text(
        f"<b>Dear {seller_link}, please select your preferred withdrawal currency:</b>\n\n"
        "Available networks for USDT:\n"
        "• TON Network\n"
        "• BEP20 (BSC)\n"
        "• TRC20 (TRON)",
        reply_markup=reply_markup,
        parse_mode="html"
    )
    await query.answer()

async def handle_coin_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
            if deal['group_id'] == group_id:
                deal_id = d_id
                break
    deal_data = get_active_deal(deal_id)

    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can select the withdrawal currency ❌", show_alert=True)
        return

    # Validate and parse the selected coin
    if not query.data or "_" not in query.data:
        await query.edit_message_text("Invalid selection. Please try again.")
        return

    # Safely extract the selected coin and network
    selected_coin = query.data.replace("coin_", "")
    if selected_coin in ['BTC', 'ETH'] and deal_data['amount'] < 3:
        await query.answer("Minimum deal amount for this coin is $3 ❌", show_alert=True)
        return
    currency, network = network_mapping.get(selected_coin, (selected_coin, selected_coin)) 
   
    print(f"Debug: selected_coin={selected_coin}, currency={currency}, network={network}")
    deal_data['selected_coin'] = currency
    deal_data['network'] = network
    update_active_deal(deal_id, {'selected_coin': currency, 'network': network})

    seller = await context.bot.get_chat(deal_data['seller'])
    seller_link = f'<a href="tg://user?id={seller.id}">{seller.first_name}</a>'

    msg = await query.edit_message_text(
        f"<b>Selected coin: {selected_coin}\nNetwork: {network}</b>\n\n"
        f"Please {seller_link}, enter your wallet address for withdrawal:",
        parse_mode="html"
    )
    context.user_data["prompt_message_id"] = msg.message_id
    context.user_data['state'] = "AWAITING_WALLET"
    await query.answer()



async def handle_confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
            if deal['group_id'] == group_id:
                deal_id = d_id
                break
    deal_data = get_active_deal(deal_id)
    from handlers import calculate_fee
    from convert import request_exchange

    amount = deal_data['amount']
    fee = calculate_fee(amount, deal_data['deal_type'])
    payout_amount = amount - fee
    selected_coin = deal_data['selected_coin']
    currency, network = network_mapping.get(selected_coin, (selected_coin, selected_coin.lower()))
    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can confirm the withdrawal ❌", show_alert=True)
        return

    payout_request = context.user_data.get('payout_request')
    if not payout_request:
        await query.edit_message_text("Error: Withdrawal information not found. Please try again.")
        return
    print(f"Payout Request Data: {payout_request}")
    if currency != "USDT":
        exchange_request = request_exchange(payout_amount, "USDT", currency)
        if not isinstance(exchange_request, dict) or 'result' not in exchange_request:
            await update.message.reply_text("Error during currency conversion. Please try again.")
            return   
    payout_result = await create_payout(**payout_request)
    print(f"Payout Result: {payout_result}")
    
    if payout_result.get('result') == 130:
        seller = await context.bot.get_chat(deal_data['seller'])
        keyboard = [[InlineKeyboardButton(f"🟢 Confirm your Payment {seller.first_name}", callback_data="seller_confirm_paid")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🌟 *Withdrawal Successfully Initiated*\n\n"
            f"💰 Amount: `{payout_request['amount']} {payout_request['currency']}`\n"
            f"🔗 Network: `{payout_request['network']}`\n"
            f"📝 Address: `{payout_request['address']}`\n\n"
            f"_Please {seller.first_name}, confirm once you have received the funds in your wallet._",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )   
    else:
        error_msg = payout_result.get('message', 'Unknown error')
        await query.edit_message_text(
            f"❌ Withdrawal failed\nError: {error_msg}\n"
            f"Please contact support."

        )
    context.user_data.clear()

async def handle_edit_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            break
    deal_data = get_active_deal(deal_id)

    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can edit the withdrawal ❌", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("Change Coin", callback_data="change_coin"),
         InlineKeyboardButton("Change Address", callback_data="change_address")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "What would you like to change?",
        reply_markup=reply_markup
    )

async def handle_change_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            break
    deal_data = get_active_deal(deal_id)

    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can edit the withdrawal ❌", show_alert=True)
        return
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data="coin_BTC"),
         InlineKeyboardButton("Ethereum", callback_data="coin_ETH")],
        [InlineKeyboardButton("TON", callback_data="coin_TON"),
         InlineKeyboardButton("SOL", callback_data="coin_SOL"),
         InlineKeyboardButton("LTC", callback_data="coin_LTC")],
        [InlineKeyboardButton("USDT (TON)", callback_data="coin_USDT_TON"),
         InlineKeyboardButton("USDT (BEP20)", callback_data="coin_USDT_BEP20")],
         [InlineKeyboardButton("POL", callback_data="coin_POL"),
        InlineKeyboardButton("DOGE", callback_data="coin_DOGE")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "★━━━━━━━━━━━━━━━━━━━━━━★\n"
        "┃ 𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘  \n"
        "★━━━━━━━━━━━━━━━━━━━━━━★\n\n"
        "Please select a new coin for withdrawal:",
        reply_markup=reply_markup
    )
    await query.answer()

async def handle_change_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            break
    deal_data = get_active_deal(deal_id)
    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can edit the withdrawal ❌", show_alert=True)
        return
    await query.answer()
    context.user_data['state'] = "AWAITING_WALLET"
    msg = await query.edit_message_text("Please enter the new wallet address for withdrawal:")
    context.user_data["prompt_message_id"] = msg.message_id

async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_deals = get_all_active_deals()
    deal_id = None
    deal_data = None
    for d_id, deal in active_deals.items():
        if deal['seller'] == update.message.from_user.id:
            deal_id = d_id
            deal_data = deal
            break
    prompt_message_id = context.user_data.get("prompt_message_id")
    if prompt_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=prompt_message_id
            )
        except:
            pass
    if not deal_data:
        context.user_data.clear()  
        context.user_data['state'] = None
        await update.message.reply_text("No active deal found. Please start a new deal.")
        return

    if update.message.from_user.id != deal_data['seller']:
        return

    wallet_address = update.message.text
    selected_coin = f"USDT_{deal_data['network']}" if deal_data['selected_coin'] == 'USDT' else deal_data['selected_coin']
    if selected_coin in ['USDT_TON', 'TON']:
        context.user_data['state'] = 'AWAITING_MEMO'
        context.user_data['wallet_address'] = wallet_address
        msg = await update.message.reply_text("Please enter the memo tag for this wallet address. If a memo tag is not required, type `skip`", parse_mode="Markdown") 
        context.user_data["prompt_message_id"] = msg.message_id     
        return

    await process_withdrawal(update, context, wallet_address)

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address, memo=None):
    context.user_data.clear()
    context.user_data['state'] = None

    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['seller'] == update.message.from_user.id:
            deal_id = d_id
            break
    deal_data = get_active_deal(deal_id)
    if not deal_data:
        await update.message.reply_text("No active deal found. Please start a new deal.")
        context.user_data.clear()
        context.user_data['state'] = None

        return
    from handlers import calculate_fee
    from convert import exchange_rate

    amount = deal_data['amount']
    fee = calculate_fee(amount, deal_data['deal_type'])
    payout_amount = amount - fee

    selected_coin = f"USDT_{deal_data['network']}" if deal_data['selected_coin'] == 'USDT' else deal_data['selected_coin']
    currency, network = network_mapping[selected_coin]

    if memo:
        wallet_address = f"{wallet_address}|{memo}"

    withdrawal_fee = WITHDRAWAL_FEES.get(currency, 0)
    payout_amount_after_fee = payout_amount - withdrawal_fee
    if currency != "USDT":
        exchange_result = exchange_rate(payout_amount_after_fee, currency)
        print(f"Exchange rate calculation response: {exchange_result}")
        if isinstance(exchange_result, dict) and 'result' in exchange_result and exchange_result['result'] == 100:
            final_payout_amount = float(exchange_result['toAmount'])
        else:
            await update.message.reply_text("Error calculating exchange rate. Please try again.")
            return
    else:
        final_payout_amount = payout_amount_after_fee
   


    payout_request = {
        "amount": final_payout_amount,
        "address": wallet_address,
        "currency": currency,
        "network": network,
        "seller_id": deal_data['seller']
    }

    if memo:
        payout_request["memo"] = memo

    keyboard = [
        [InlineKeyboardButton("Yes, Proceed", callback_data="confirm_withdrawal"),
         InlineKeyboardButton("No, Edit", callback_data="edit_withdrawal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    confirmation_message = (
        "★━━━━━━━━━━━━━━━━━━━★\n"
        "┃ 𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘  \n"
        "★━━━━━━━━━━━━━━━━━━━★\n\n"
        "📤 *Withdrawal Details*\n\n"
        f"💰 *Amount:* `{final_payout_amount:.4f} {currency}`\n"
        f"🌐 *Network:* `{network}`\n"
        f"📍 *Address:* `{wallet_address}`\n"
        f"💸 *Network Fee:* `{withdrawal_fee} {currency}`\n"
        f"{f'🔖 *Memo:* `{memo}`' if memo else ''}\n\n"
        "⚠️ Please review and confirm the above details carefully.\n\n"
        "Do you want to proceed?"
    )
    await update.message.reply_text(confirmation_message, reply_markup=reply_markup,parse_mode="Markdown")
    context.user_data['payout_request'] = payout_request

async def handle_memo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'AWAITING_MEMO':
        context.user_data.clear()
        context.user_data['state'] = None
        return
    prompt_message_id = context.user_data.get("prompt_message_id")
    if prompt_message_id:
        await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_message_id
                )
    memo = update.message.text
    wallet_address = context.user_data.get('wallet_address')
    group_id = update.effective_chat.id

    active_deals = get_all_active_deals()
    deal_id = None
    deal_data = None
    
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id and deal['seller'] == update.message.from_user.id:
            deal_id = d_id
            deal_data = deal
            break


    if memo.lower() == 'skip':
        memo = None

    # Use the correct selected_coin format
    selected_coin = f"USDT_{deal_data['network']}" if deal_data['selected_coin'] == 'USDT' else deal_data['selected_coin']
    
    await process_withdrawal(update, context, wallet_address, memo)
    context.user_data['state'] = None
