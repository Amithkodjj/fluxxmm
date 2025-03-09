from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json
from config import *
from utils import *
from withdrawal import *
from deposit import *
from datetime import datetime
from refund import *
from datetime import datetime,  timedelta
from telegram.error import BadRequest
from login import *
from telethon.tl.functions.messages import CreateChatRequest
from telethon.tl.functions.messages import ExportChatInviteRequest

def load_fees():
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config['p2p_fee'], config['bs_fee'], config['allfee']

def calculate_fee(amount, deal_type):
    p2p_fee, bs_fee, allfee = load_fees()
    if deal_type == "p2p":
        fee_percentage = p2p_fee
    elif deal_type == "b_and_s":
        fee_percentage = bs_fee
    else:
        fee_percentage = allfee
    return amount * (fee_percentage / 100)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Start Deal 🤝", callback_data="start_deal")],
        [InlineKeyboardButton("Help ⚠️", callback_data="help"),
         InlineKeyboardButton("Reviews 🌟", callback_data="reviews")],
        [InlineKeyboardButton("Contact Mod 📞", url="https://t.me/echofluxxx")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝘁𝗵𝗲 𝗠𝗶𝗱𝗱𝗹𝗲𝗺𝗮𝗻 𝗕𝗼𝘁! 🤝\n"
        "𝗪𝗲 𝗵𝗲𝗹𝗽 𝗽𝗲𝗼𝗽𝗹𝗲 𝗯𝘂𝘆 𝗮𝗻𝗱 𝘀𝗲𝗹𝗹 𝘁𝗵𝗶𝗻𝗴𝘀 𝘀𝗮𝗳𝗲𝗹𝘆.\n\n"
        "📝 Quick Deal Setup:\n"
        "Use the /form command in any group to quickly create a deal!\n\n"
        "How to use /form:\n"
        "1. Add bot to your group\n" 
        "2. Type /form\n"
        "3. Fill details as shown:\n"
        "   <code>Buyer: @username\n"
        "   Seller: @username\n" 
        "   Deal: What you're trading\n"
        "   Price: $amount\n\n</code>"
        "4. Click The Text To Copy Deal Form 👆\n\n"
        "Both buyer and seller must be in the group! 🎯"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def handle_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command can only be used in a group.")
        return
        
    context.user_data['awaiting_form'] = True
    await update.message.reply_text(
        "Please enter deal details in this format:\n\n"
        "Buyer: @username\n"
        "Seller: @username\n"
        "Deal: What you're dealing\n"
        "Price: $amount\n\n"
        "```Example:\n\n"
        "Buyer: @buyer\n"
        "Seller: @seller\n"
        "Deal: Selling ps4\n"
        "Price: $2000```\n\n"
        '⚠ Your form data must be exactly how the instruction is given ⚠'
        '⚠ State price in dollar and ensure you include the $ sign ⚠',
        parse_mode="Markdown"
    )


from telethon import TelegramClient
import os

async def check_admin_session():
    if not os.path.exists('admin_session.session'):
        return False
    
    client = TelegramClient('admin_session', API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        await client.disconnect()
        return True
    except:
        return False

async def process_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_form'):
        print(">>> Not awaiting form, returning early")
        return
        
    text = update.message.text
    lines = text.split('\n')
    form_data = {}
    entities = update.message.entities
    
    print(f">>> Starting form processing with {len(lines)} lines")
    print(f">>> Raw text: {text}")
    print(f">>> Entities found: {entities}")
    
    try:
        for line in lines:
            line = line.replace('  ', ' ') 
            print(f">>> Processing line: {line}")
            
            if line.lower().startswith('buyer:'):
                print(">>> Processing buyer...")
                if not await check_admin_session():
                    print(">>> Admin session check failed")
                    await update.message.reply_text("Admin needs to login ⚠")
                    return
                    
                client = TelegramClient('admin_session', API_ID, API_HASH)
                await client.connect()
                buyer_found = False
                
                for entity in entities:
                    if entity.type in ['text_mention', 'mention']:
                        entity_text = text[entity.offset:entity.offset + entity.length]
                        print(f">>> Found buyer entity: {entity_text}")
                        print(f">>> Entity offset: {entity.offset}, length: {entity.length}")
                        print(f">>> Checking if {entity_text} is in {line}")
                        
                        if entity_text in line:
                            try:
                                print(f">>> Attempting to get entity for {entity_text}")
                                user = await client.get_entity(entity_text)
                                form_data['buyer_id'] = user.id
                                form_data['buyer_name'] = user.first_name
                                print(f">>> Successfully resolved buyer: {form_data['buyer_name']} (ID: {form_data['buyer_id']})")
                                buyer_found = True
                            except Exception as e:
                                print(f">>> Error resolving buyer entity: {e}")
                                await client.disconnect()
                                await update.message.reply_text("Admin needs to login ⚠")
                                return
                
                if not buyer_found:
                    print(">>> No buyer entity was matched in the line")
                    await update.message.reply_text(
                                    "💡 Form Guide:\n\n"
                                    "1. Make sure usernames are correct\n"
                                    "2. Both users must be in the group\n"
                                    "3. Try copying the format below:\n\n"
                                    "<code>Buyer: @username\n"
                                    "Seller: @username\n"
                                    "Deal: item description\n"
                                    "Price: $amount</code>",
                                    parse_mode='HTML'
                                )
                await client.disconnect()

            elif line.lower().startswith('seller:'):
                print(">>> Processing seller...")
                if not await check_admin_session():
                    print(">>> Admin session check failed")
                    await update.message.reply_text("Admin needs to login ⚠")
                    return
                    
                client = TelegramClient('admin_session', API_ID, API_HASH)
                await client.connect()
                seller_found = False
                
                for entity in entities:
                    if entity.type in ['text_mention', 'mention']:
                        entity_text = text[entity.offset:entity.offset + entity.length]
                        print(f">>> Found seller entity: {entity_text}")
                        print(f">>> Entity offset: {entity.offset}, length: {entity.length}")
                        print(f">>> Checking if {entity_text} is in {line}")
                        
                        if entity_text in line:
                            try:
                                print(f">>> Attempting to get entity for {entity_text}")
                                user = await client.get_entity(entity_text)
                                form_data['seller_id'] = user.id
                                form_data['seller_name'] = user.first_name
                                print(f">>> Successfully resolved seller: {form_data['seller_name']} (ID: {form_data['seller_id']})")
                                seller_found = True
                            except Exception as e:
                                print(f">>> Error resolving seller entity: {e}")
                                await client.disconnect()
                                await update.message.reply_text("Admin needs to login ⚠")
                                return
                
                if not seller_found:
                    print(">>> No seller entity was matched in the line")
                await client.disconnect()

            elif line.lower().startswith('deal:'):
                deal_type = line.split('Deal:')[1].strip()
                form_data['deal_type'] = deal_type
                print(f">>> Added deal_type: {deal_type}")
                
            elif line.lower().startswith('price:'):
                try:
                    # Handle different price formats
                    price_text = line.split(':', 1)[1].strip()
                    price_text = price_text.replace('$', '').strip()
                    price_text = price_text.replace('usd', '').strip()
                    amount = float(price_text)
                    form_data['amount'] = amount
                except:
                    await update.message.reply_text(
                        "💡 Price should be a number like:\n"
                        "Price: $100\n"
                        "Price: 100\n"
                        "Price: 100.50"
                    )
                    return
        
        print(f">>> Form data collected: {form_data}")
        required_fields = ['buyer_id', 'buyer_name', 'seller_id', 'seller_name', 'deal_type', 'amount']
        missing_fields = [field for field in required_fields if field not in form_data]
        
        print(f">>> Required fields: {required_fields}")
        print(f">>> Missing fields: {missing_fields}")
        
        if not all(k in form_data for k in ['buyer_id', 'buyer_name', 'seller_id', 'seller_name', 'deal_type', 'amount']):
            keyboard = [[InlineKeyboardButton("❌ Cancel Form", callback_data="cancel_form")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Form not arranged correctly ❌\n\n"
                "💡 Copy and fill this format:\n"
                "<code>Buyer: @username\n"
                "Seller: @username\n"
                "Deal: what you're trading\n"
                "Price: $amount</code>",
                parse_mode='HTML'
            )
            return
            
        deal_id = generate_deal_id(form_data['buyer_id'], None, update.effective_chat.id)
        print(f">>> Generated deal_id: {deal_id}")
        
        deal_data = {
            "status": "initiated",
            "starter": update.effective_user.id,
            "group_id": update.effective_chat.id,
            "buyer": form_data['buyer_id'],
            "seller": form_data['seller_id'],
            "amount": form_data['amount'],
            "deal_type": form_data['deal_type'],
            "timestamp": datetime.now().isoformat()
        }
        
        print(f">>> Deal data prepared: {deal_data}")
        save_active_deal(deal_id, deal_data)
        
        keyboard = [
            [InlineKeyboardButton("Click Confirm ✅", callback_data=f"confirm_form_{deal_id}")],
            [InlineKeyboardButton("End Deal ❌", callback_data=f"back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
            f"👤 Buyer: <a href='tg://user?id={form_data['buyer_id']}'>{form_data['buyer_name']}</a>\n"
            f"👥 Seller: <a href='tg://user?id={form_data['seller_id']}'>{form_data['seller_name']}</a>\n"
            f"🔵 Deal: {form_data['deal_type']}\n"
            f"💰 Amount: ${form_data['amount']:.2f}\n\n"
            f"<i>Both buyer and seller must confirm to proceed</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        context.user_data['awaiting_form'] = False
        print(">>> Form processing completed successfully")
        
    except Exception as e:
        print(f">>> CRITICAL ERROR processing form: {str(e)}")
        print(f">>> Exception type: {type(e)}")
        import traceback
        print(f">>> Traceback: {traceback.format_exc()}")
        await update.message.reply_text("Invalid form format or user not found. Please try again.")
        context.user_data['awaiting_form'] = False

async def handle_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    formatted_reviews = review_system.get_formatted_reviews()
    
    if not formatted_reviews:
        keyboard = [[InlineKeyboardButton("Back 🔙", callback_data="mainmenu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "No reviews available yet. Be the first to complete a deal! 🌟",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
        
    review_text = (
        "<b>🌟 SELLER REVIEWS</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )
    
    for seller_id, data in formatted_reviews.items():
        review_text += (
            f"<b>👤 <a href='tg://user?id={seller_id}'>{data['name']}</a></b>\n"
            f"P2P Trade 🤝: {data['p2p_trades']}\n"
            f"Buy & Sell 💎: {data['bs_trades']}\n"
            f"<b>Total Rating:</b> <b>👍 {data['positive_trades']} | 👎 {data['negative_trades']}</b>\n\n"
            f"<i>Buyers that Rated:</i>\n"
        )
        
        for reviewer_id, reviewer_data in data['reviewers'].items():
            review_text += (
                f"• <a href='tg://user?id={reviewer_id}'>{reviewer_data['name']}</a>"
                f" (👍{reviewer_data['positive']} | 👎{reviewer_data['negative']})\n"
            )
        
        review_text += "\n━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = [[InlineKeyboardButton("Back 🔙", callback_data="mainmenu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        review_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    await query.edit_message_text(
        review_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    groups_text = "<b>🔍 Bot's Group List:</b>\n\n"
    
    try:
        # Get bot's updates to find groups
        updates = await context.bot.get_updates()
        seen_groups = set()
        
        for update in updates:
            if update.message and update.message.chat:
                chat = update.message.chat
                if chat.type in ['group', 'supergroup'] and chat.id not in seen_groups:
                    try:
                        invite_link = await context.bot.export_chat_invite_link(chat.id)
                        groups_text += f"📌 <b>{chat.title}</b>\n"
                        groups_text += f"🔗 Link: {invite_link}\n\n"
                        seen_groups.add(chat.id)
                    except Exception:
                        groups_text += f"📌 <b>{chat.title}</b>\n"
                        groups_text += "❌ Could not generate invite link\n\n"
                        seen_groups.add(chat.id)

        await update.message.reply_text(groups_text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error fetching groups: {str(e)}")


async def handle_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session():
        await update.message.reply_text("Admin needs to login first!")
        return
        
    client = TelegramClient('admin_session', API_ID, API_HASH)
    await client.connect()
    
    try:
        # Create the group with specified title and add the user
        result = await client(CreateChatRequest(
            users=[update.effective_user.username],
            title="𝙵𝙻𝚄𝚇𝚇 𝙴𝚂𝙲𝚁𝙾𝚆 𝙶𝚁𝙾𝚄𝙿"
        ))
        
        chat_id = result.chat.id
        
        # Generate private invite link
        invite = await client(ExportChatInviteRequest(
            peer=chat_id,
            legacy_revoke_permanent=True,
            expire_date=None,
            usage_limit=None
        ))
        
        await update.message.reply_text(
            "✅ Group created successfully!\n\n"
            f"Title: 𝙵𝙻𝚄𝚇𝚇 𝙴𝚂𝙲𝚁𝙾𝚆 𝙶𝚁𝙾𝚄𝙿\n"
            f"Join here: {invite.link}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"{str(e)}")
    finally:
        await client.disconnect()

async def handle_startdeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command can only be used in a group.")
        return

    active_deals = get_all_active_deals()
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            if deal['status'] == 'completed':
                remove_active_deal(d_id)
                continue
            await update.message.reply_text("There's already an active deal in this group. Please wait for it to complete.")
            return

    deal_id = generate_deal_id(user_id, None, group_id)
    context.chat_data['deal_id'] = deal_id
    context.chat_data['deal_starter'] = user_id
    
    deal_data = {
        "status": "initiated",
        "starter": user_id,
        "group_id": group_id,
        "buyer": None,
        "seller": None,
        "amount": None,
        "deal_type": None,
        "timestamp": datetime.now().isoformat()
    }
    save_active_deal(deal_id, deal_data)
    keyboard = [
        [InlineKeyboardButton("Buyer", callback_data="buyer"),
         InlineKeyboardButton("Seller", callback_data="seller")],
        [InlineKeyboardButton("Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "A new deal has been started. Please select your role:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    group_id = message.chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            break
    deal_data = get_active_deal(deal_id) if deal_id else None

    if query.data in ["buyer", "seller"] and not deal_data:
        user_id = query.from_user.id
        group_id = update.effective_chat.id
        deal_id = generate_deal_id(user_id, None, group_id)
        
        deal_data = {
            "status": "initiated",
            "starter": user_id,
            "group_id": group_id,
            "buyer": None,
            "seller": None,
            "amount": None,
            "deal_type": None,
            "timestamp": datetime.now().isoformat()
        }
        save_active_deal(deal_id, deal_data)
        context.chat_data['deal_id'] = deal_id

    
    if query.data == "start_deal":
        if update.effective_chat.type not in ['group', 'supergroup', 'channel']:
            await query.answer("This command can only be used in a group or channel ❌", show_alert=True)
            return
        user_id = query.from_user.id
        group_id = update.effective_chat.id
        deal_id = generate_deal_id(user_id, None, group_id)

        active_deals = get_all_active_deals()
        for d_id, deal in active_deals.items():
            if deal['group_id'] == group_id:
                if deal['status'] == 'completed':
                    remove_active_deal(d_id)
                    continue
                await query.answer("There's already an active deal in this group ❌\n\n Please wait for it to complete.")
                return

        
        # Save initial deal data
        deal_data = {
            "status": "initiated",
            "starter": user_id,
            "group_id": group_id,
            "buyer": None,
            "seller": None,
            "amount": None,
            "deal_type": None,
            "timestamp": datetime.now().isoformat()
        }
        save_active_deal(deal_id, deal_data)
        context.chat_data['deal_id'] = deal_id
        keyboard = [
            [InlineKeyboardButton("Buyer", callback_data="buyer"),
             InlineKeyboardButton("Seller", callback_data="seller")],
            [InlineKeyboardButton("Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            format_text("FLUXX ESCROW SERVICE\n\nPlease select your role:", "italic"),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
   
    if query.data in ["buyer", "seller"]:
        if deal_data[query.data] is not None:
            await query.answer(f"{deal_data[query.data]} already clicked {query.data.capitalize()}", show_alert=True)
            return

        if query.from_user.id == deal_data['buyer'] or query.from_user.id == deal_data['seller']:
            await query.answer("You've already selected a role", show_alert=True)
            return

        deal_data[query.data] = query.from_user.id
        update_active_deal(deal_id, {query.data: query.from_user.id})

        if deal_data['buyer'] and deal_data['seller']:
            buyer = await context.bot.get_chat(deal_data['buyer'])
            seller = await context.bot.get_chat(deal_data['seller'])
            
            keyboard = [
                [InlineKeyboardButton("P2P Trade", callback_data="p2p"),
                InlineKeyboardButton("Buy & Sell", callback_data="b_and_s")],
                [InlineKeyboardButton("Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Determine which role was filled first
            first_role = 'buyer' if deal_data['buyer'] != query.from_user.id else 'seller'
            first_user = buyer if first_role == 'buyer' else seller
            second_role = 'seller' if first_role == 'buyer' else 'buyer'
            
            await context.bot.send_message(  
                chat_id=group_id,  
                text=(  
                    f"ℋ𝑒𝓁𝓁𝑜, <a href='tg://user?id={first_user.id}'>{first_user.first_name}</a>, the 𝑟𝑜𝑙𝑒 {second_role} has been claimed by <a href='tg://user?id={query.from_user.id}'>{query.from_user.first_name}</a>. You can now proceed with 𝑑𝑒𝑎𝑙 selection "
                   
               ),
                parse_mode="HTML"
            )
            
            await query.edit_message_text(
                "<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
                f"Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
                f"Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>\n\n"
                f"𝗕𝘂𝘆𝗲𝗿, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗰𝗵𝗼𝗼𝘀𝗲 𝘁𝗵𝗲 𝘁𝘆𝗽𝗲 𝗼𝗳 𝗱𝗲𝗮𝗹:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            buyer_text = 'Not selected'
            seller_text = 'Not selected'
            
            if deal_data['buyer']:
                buyer = await context.bot.get_chat(deal_data['buyer'])
                buyer_text = f"<a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>"
            
            if deal_data['seller']:
                seller = await context.bot.get_chat(deal_data['seller'])
                seller_text = f"<a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>"
            
            await query.edit_message_text(
                f"Buyer: {buyer_text}\nSeller: {seller_text}\n\nWaiting for both roles to be filled.",
                reply_markup=query.message.reply_markup,
                parse_mode='HTML'
            )

    elif query.data in ["p2p", "b_and_s"]:
        if query.from_user.id != deal_data['buyer']:
            await query.answer("Only the buyer can select the deal type", show_alert=True)
            return

        deal_type_display = "P2P Trade" if query.data == "p2p" else "Buy & Sell"
        deal_data["deal_type"] = query.data
        update_active_deal(deal_id, {"deal_type": query.data})
        buyer = await context.bot.get_chat(deal_data['buyer'])
        seller = await context.bot.get_chat(deal_data['seller'])
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel Deal", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = await query.edit_message_text(
            f"<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
            f"👤 Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
            f"👥 Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>\n\n"
            f"🔵 Deal Type: <b>{deal_type_display}</b>\n\n"
            f"💰 <b>Enter Deposit Amount</b>\n"
            f"• Only numbers (e.g. 100 or 100.50)\n"
            f"• Minimum amount: $1\n"
            f"• Maximum amount: $100,000\n"
            f"• Admin fee: 5% of transaction amount\n"
            f"• Purpose: Secure escrow service for safe trading\n"
            f"• Your funds will be held safely until transaction is complete\n"
            f"• Instant release upon mutual confirmation\n\n"
            f"<i>Waiting for buyer to enter amount...</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )        
        context.user_data["state"] = "AMOUNT"  
        context.user_data["deal_type"] = query.data  
        context.user_data["prompt_message_id"] = msg.message_id


    elif query.data == "help":
        keyboard = [
            [InlineKeyboardButton("English 🇬🇧", callback_data="help_en"),
             InlineKeyboardButton("Hindi 🇮🇳", callback_data="help_hi")],
            [InlineKeyboardButton("Back 🔙", callback_data="mainmenu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Select your preferred language for help:",
            reply_markup=reply_markup
        )
    
    elif query.data == "cancel_form":
        context.user_data.clear()
        await query.message.delete()

    elif query.data.startswith("help_"):
        await handle_help_language(update, context)
    elif query.data == "reviews":
        await handle_reviews(update, context)
    elif query.data == "release_payment":
        await handle_release_payment(update, context)

    elif query.data.startswith("coin_"):
        await handle_coin_selection(update, context)

    elif query.data.startswith("confirm_form_"):
        deal_id = query.data.split("_")[2]
        deal_data = get_active_deal(deal_id)
        
        if not deal_data:
            await query.answer("Deal not found", show_alert=True)
            return
            
        if query.from_user.id not in [deal_data['buyer'], deal_data['seller']]:
            await query.answer("Only buyer and seller can confirm", show_alert=True)
            return
            
        if 'confirmations' not in deal_data:
            deal_data['confirmations'] = []
            
        if query.from_user.id in deal_data['confirmations']:
            await query.answer("You've already confirmed", show_alert=True)
            return
            
        deal_data['confirmations'].append(query.from_user.id)
        update_active_deal(deal_id, {'confirmations': deal_data['confirmations']})

        if len(deal_data['confirmations']) == 1:
            other_user_id = deal_data['seller'] if query.from_user.id == deal_data['buyer'] else deal_data['buyer']
            other_user = await context.bot.get_chat(other_user_id)
            await query.message.reply_text(
                f"Waiting for <a href='tg://user?id={other_user_id}'>{other_user.first_name}</a> to confirm",
                parse_mode='HTML'
            )
        
        if len(deal_data['confirmations']) == 2:
            # Both confirmed, proceed to deposit
            invoice = await create_invoice(deal_data['amount'], deal_id)
            if invoice.get("message") == "success" and invoice.get("result") == 100:
                payment_url = invoice["payLink"]
                track_id = invoice["trackId"]
                
                keyboard = [
                    [InlineKeyboardButton("🔗 Pay Now", url=payment_url)],
                    [InlineKeyboardButton("❌ End Deal", callback_data="back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
                    f"Please complete your payment of ${deal_data['amount']:.2f}\n\n"
                    f"Use the Payment Link Below 👇\n"
                    f"Track ID: <code>{track_id}</code>\n"
                    "<code>⚠ Do Not Reuse This Link</code>\n"
                    "<code>⚠ Buyer must pay exact amount as seen in Link</code>",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.answer("Confirmation received, waiting for other party", show_alert=True)


    elif query.data == "seller_confirm_paid":
        await handle_seller_confirm(update, context)
    elif query.data == "confirm_withdrawal":
        await handle_confirm_withdrawal(update, context)
    elif query.data == "edit_withdrawal":
        await handle_edit_withdrawal(update, context)
    elif query.data == "change_coin":
        await handle_change_coin(update, context)
    elif query.data == "change_address":
        await handle_change_address(update, context)
    elif query.data == "mainmenu":
        await handle_start(update, context)
    elif query.data == "mod":
        user_id = query.from_user.id
        context.user_data['awaiting_complaint'] = True
        context.user_data['complaint_message_id'] = query.message.message_id
        await query.answer()
        await query.message.reply_text("Please type your complaint message.")

    elif query.data.startswith("review_"):
        _, action, seller_id = query.data.split("_")
        active_deals = get_all_active_deals()
        deal_data = None
        for deal in active_deals.values():
            if deal['seller'] == int(seller_id):
                deal_data = deal
                break
        
        if query.from_user.id != deal_data['buyer']:
            await query.answer("Only the buyer can leave a review ❌", show_alert=True)
            return
        seller = await context.bot.get_chat(int(seller_id))
        buyer = await context.bot.get_chat(deal_data['buyer'])
        
        if action == "positive":
            review_system.add_review(int(seller_id), seller.first_name, True, deal_data['deal_type'],  buyer.id, buyer.first_name)
            await query.edit_message_text(
                f"✅ You rated {seller.first_name} positively!\n\n"
                "Thank you for your feedback."
            )
        elif action == "negative":
            review_system.add_review(int(seller_id), seller.first_name, False, deal_data['deal_type'],  buyer.id, buyer.first_name)
            await query.edit_message_text(
                f"❌ You rated {seller.first_name} negatively.\n\n"
                "Thank you for your feedback."
            )
    elif query.data == "back":
        query = update.callback_query
        message = query.message
        group_id = message.chat.id
        active_deals = get_all_active_deals()
        deal_id = None
        for d_id, deal in active_deals.items():
            if deal['group_id'] == group_id:
                deal_id = d_id
                break
        if deal_id:
            deal_data = get_active_deal(deal_id)
            if deal_data:
                if deal_data.get('status') in ['waiting', 'deposited']:
                    if str(query.from_user.id) == ADMIN_ID:
                        remove_active_deal(deal_id)
                        context.user_data.clear()
                        context.user_data["state"] = None
                        if 'buyer' in deal_data:
                            context.user_data.pop('buyer', None)
                        if 'seller' in deal_data:
                            context.user_data.pop('seller', None)
                        
                        user_link = f'<a href="tg://user?id={query.from_user.id}">{query.from_user.first_name}</a>'
                        await query.edit_message_text(f"Deal cancelled by Admin {user_link}.", parse_mode="html")
                    else:
                        await query.answer("Only Moderator can cancel deals at this stage ❌", show_alert=True)
                else:
                    if query.from_user.id == deal_data['starter'] or str(query.from_user.id) == ADMIN_ID:
                        remove_active_deal(deal_id)
                        context.user_data.clear()
                        context.user_data["state"] = None
                        if 'buyer' in deal_data:
                            context.user_data.pop('buyer', None)
                        if 'seller' in deal_data:
                            context.user_data.pop('seller', None)
                        
                        user_link = f'<a href="tg://user?id={query.from_user.id}">{query.from_user.first_name}</a>'
                        await query.edit_message_text(f"Deal cancelled by {user_link}.", parse_mode="html")
                    else:
                        await query.answer("You are not authorized to cancel this deal ❌", show_alert=True)
            else:
                await query.answer("No active deal found.", show_alert=True)


    elif query.data.startswith("refunds_"):
        await handle_refund_coin_selection(update, context)

    elif query.data == "check_timer":
        group_id = update.effective_chat.id
        active_deals = get_all_active_deals()
        deal_id = None
        for d_id, deal in active_deals.items():
            if deal['group_id'] == group_id:
                deal_id = d_id
                break
                
        if not deal_id:
            await query.answer("No active deal found", show_alert=True)
            return
            
        deal_data = get_active_deal(deal_id)
        remaining_time = get_remaining_time(deal_data.get('payment_time'))
        
        buyer = await context.bot.get_chat(deal_data['buyer'])
        seller = await context.bot.get_chat(deal_data['seller'])
        
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
        
        await query.edit_message_text(
            f"<b>⚠️ FLUXX ESCROW BOT - PAYMENT CONFIRMED ✅</b>\n\n"
            f"💵 <b>Deposit Amount:</b> ${amount:.2f}\n"
            f"✅ <b>Payment confirmed by:</b> <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
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
            f"<b>⏱ Time Remaining to Complete Trade: {remaining_time} Minutes</b> \n"
            f"⚠️ <i>Please complete the trade before the timer expires, or a moderator will be involved automatically.</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    await query.answer()

def get_remaining_time(payment_time):
    if not payment_time:
        return "00:00"
    payment_datetime = datetime.fromisoformat(payment_time)
    time_limit = payment_datetime + timedelta(minutes=60)
    remaining = time_limit - datetime.now()
    
    if remaining.total_seconds() <= 0:
        return "00:00"
        
    minutes = int(remaining.total_seconds() // 60)
    seconds = int(remaining.total_seconds() % 60)
    return f"{minutes:02d}:{seconds:02d}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "AMOUNT":
        if not update.message.reply_to_message or update.message.reply_to_message.message_id != context.user_data.get("prompt_message_id"):
            return
        try:
            prompt_message_id = context.user_data.get("prompt_message_id")
            if prompt_message_id:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_message_id
                )
            amount = float(update.message.text)
            if amount < 1 or amount > 100000:
                msg = await update.message.reply_text("Amount must be between $1 and $100,000")
                context.user_data["prompt_message_id"] = msg.message_id
                return
                
            group_id = update.effective_chat.id
            active_deals = get_all_active_deals()
            deal_id = None

            for d_id, deal in active_deals.items():
                if deal['group_id'] == group_id:
                    deal_id = d_id
                    deal_data = deal
                    break

            if not deal_id:
                await update.message.reply_text("No active deal found. Please start a new deal.")
                context.user_data.clear()
                context.user_data["state"] = None
                return
            deal_data = get_active_deal(deal_id)
            deal_type = context.user_data.get("deal_type")
            fee = calculate_fee(amount, deal_type)
            total = amount + fee
            invoice = await create_invoice(total, deal_id)
            if invoice.get("message") == "success"and invoice.get("result") == 100:
                payment_url = invoice["payLink"]
                track_id = invoice["trackId"]
                
                deal_data['amount'] = total
                update_active_deal(deal_id, {
                    'amount': amount,
                    'status': 'waiting'  
                })
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔗 Pay Now", url=payment_url
                        )
                    ],
                    [
                        InlineKeyboardButton("❌ End Deal", callback_data="back")
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg = await update.message.reply_text(
                    f"<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
                    f"Please complete your payment of ${total:.3f}\n\n"
                    f"Use the Payment Link Below 👇\n"
                    f"Track ID: <code>{track_id}</code>\n"
                    "<code>⚠ Do Not Reuse This Link</code>\n"
                    "<code>⚠Buyer must pay exact amount as seen in Link</code>",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                context.user_data["prompt_message_id"] = msg.message_id
            else:
                await update.message.reply_text("Error creating payment invoice. Please try again.")
            context.user_data.clear()
        except ValueError:
            keyboard = [[InlineKeyboardButton("❌", callback_data="cancel_form")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            msg = await update.message.reply_text("Please enter a valid number ⚠️",reply_markup='reply_markup', parse_mode='HTML')
            context.user_data["prompt_message_id"] = msg.message_id
    elif context.user_data.get("state") == "AWAITING_REFUND_WALLET":
        await handle_refund_address(update, context)
    elif context.user_data.get("state") == "AWAITING_WALLET":
        await handle_wallet_address(update, context)
    elif context.user_data.get('awaiting_complaint'):
        await handle_complaint(update, context)
    elif context.user_data.get("state") == "AWAITING_MEMO":
        await handle_memo_input(update, context)
    elif context.user_data.get('awaiting_code'):
        await handle_code(update, context)
    elif context.user_data.get('awaiting_password'):
        await handle_2fa_password(update, context)
    else:
        await process_form(update, context)


async def handle_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    complaint_text = update.message.text
    group_id = update.effective_chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    deal_data = None
    
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            deal_data = deal
            break

    if not deal_data:
        await update.message.reply_text("Error: No active deal found.")
        return

    if user_id not in [deal_data['buyer'], deal_data['seller']]:
        await update.message.reply_text("You are not authorized to submit a complaint for this deal.")
        return

    complaint_message_id = context.user_data.get('complaint_message_id')
    if not complaint_message_id:
        await update.message.reply_text("Error: Unable to locate the original message.")
        return
    
    prompt_message_id = context.user_data.get("prompt_message_id")
    if prompt_message_id:
        await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=prompt_message_id
                )

    message_link = f"https://t.me/c/{str(update.effective_chat.id)[4:]}/{complaint_message_id}"

    admin_message = (
        "╔══════════════════════╗\n"
        "║   FLUXX ESCROW SERVICE \n"
        "╚══════════════════════╝\n\n"
        "*COMPLAINT REPORT ⚠*\n"
        "───────────────────\n\n"
        f"*Deal Information:*\n"
        f"• Deal ID: `{deal_id}`\n"
        f"• Transaction Amount: `${deal_data['amount']:.2f}`\n\n"
        f"*Complainant Details:*\n"
        f"• User ID: `{user_id}`\n"
        f"• Role: `{'Buyer' if user_id == deal_data['buyer'] else 'Seller'}`\n\n"
        f"*Complaint Statement:*\n"
        f"`{complaint_text}`\n\n"
        f"*Reference:*\n"
        f"• Original Message:\n `{message_link}`"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
        await update.message.reply_text("*Your complaint has been sent to the admin ✅*\n\n They will review it shortly.", parse_mode="Markdown")
    except Exception as e:
        print(f"Error sending complaint to admin: {e}")
        await update.message.reply_text("There was an error submitting your complaint. Please try again")

    context.user_data.pop('awaiting_complaint', None)
    context.user_data.pop('complaint_message_id', None)

async def handle_p2pfee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        new_fee = float(context.args[0])
        if 1 <= new_fee <= 40:
            with open('config.json', 'r') as f:
                config = json.load(f)
            config['p2p_fee'] = new_fee
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            await update.message.reply_text(f"P2P fee updated to {new_fee}%")
        else:
            await update.message.reply_text("Fee must be between 1 and 40%")
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a valid fee percentage")

async def handle_bsfee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        new_fee = float(context.args[0])
        if 1 <= new_fee <= 40:
            with open('config.json', 'r') as f:
                config = json.load(f)
            config['bs_fee'] = new_fee
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            await update.message.reply_text(f"Buy & Sell fee updated to {new_fee}%")
        else:
            await update.message.reply_text("Fee must be between 1 and 40%")
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a valid fee percentage")

async def handle_setfee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        new_fee = float(context.args[0])
        if 1 <= new_fee <= 40:
            with open('config.json', 'r') as f:
                config = json.load(f)
            config['allfee'] = new_fee
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            await update.message.reply_text(f"General fee updated to {new_fee}%")
        else:
            await update.message.reply_text("Fee must be between 1 and 40%")
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a valid fee percentage")


async def handle_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /trades command - sends the trades.txt file to admin"""
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        with open("trades.txt", "r") as f:
            trades = f.read()
        if not trades:
            await update.message.reply_text("No trades found.")
            return
        # Send the trades.txt file directly
        await update.message.reply_document(
            document=trades.encode(),
            filename="trades.txt",
            caption="Here are all the trades."
        )
    except FileNotFoundError:
        await update.message.reply_text("No trades found.")



async def handle_seller_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if query.from_user.id != deal_data['seller']:
        await query.answer("Only the seller can confirm the payment ❌", show_alert=True)
        return

    deal_data['status'] = 'completed'
    update_active_deal(deal_id, {'status': 'completed'})

    save_trade(
        buyer=deal_data['buyer'],
        seller=deal_data['seller'],
        amount=deal_data['amount'],
        status='successful'
    )

    await query.edit_message_text("Payment confirmed ✅\n\n The deal has been marked as successful.")
    keyboard = [
            [InlineKeyboardButton("👍", callback_data=f"review_positive_{deal_data['seller']}"),
             InlineKeyboardButton("👎", callback_data=f"review_negative_{deal_data['seller']}")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    seller = await context.bot.get_chat(deal_data['seller'])
    buyer = await context.bot.get_chat(deal_data['buyer'])

    feedback_text = (
        "🎉 <b>Deal Successfully Completed!</b>\n\n"
        f"Hey <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>,\n"
        f"How was your experience with <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>?\n\n"
        "Please leave your feedback below 👇"
    )

    await context.bot.send_message(
        chat_id=group_id,
        text=feedback_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    sticker_id = config.get('success_sticker_id')
    if sticker_id and sticker_id.lower() != 'nosticker':
        try:
            await context.bot.send_sticker(chat_id=query.message.chat_id, sticker=sticker_id)
        except Exception as e:
            print(f"Error sending sticker: {e}")

    await query.answer()

async def handle_setsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if update.message.reply_to_message and update.message.reply_to_message.sticker:
        new_sticker_id = update.message.reply_to_message.sticker.file_id
        
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        config['success_sticker_id'] = new_sticker_id
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        await update.message.reply_text(f"Success sticker updated to: ```{new_sticker_id}```", parse_mode='Markdown')
    else:
        await update.message.reply_text("Please reply to a sticker with this command to set it as the success sticker.")


async def handle_killdeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    target_user = None
    group_id = update.effective_chat.id

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user.id
    
    elif context.args:
        if update.message.entities and len(update.message.entities) > 1:
            for entity in update.message.entities:
                if entity.type == 'text_mention':
                    target_user = entity.user.id
                    break
        
        if not target_user:
            user_input = context.args[0]
            
            if user_input.startswith('@'):
                try:
                    username = user_input.lstrip('@') 
                    chat_member = await context.bot.getChatMember(group_id, username)
                    target_user = chat_member.user.id
                except BadRequest:
                    await update.message.reply_text(f"❌ User {user_input} not found in this group.")
                    return
            
            # Handle direct user ID
            else:
                try:
                    target_user = int(user_input)
                except ValueError:
                    await update.message.reply_text("❌ Invalid input. Use @username, mention user, or use user ID.")
                    return
    else:
        await update.message.reply_text("ℹ️ Usage: Reply to user, /killdeal @username, or /killdeal user_id")
        return

    active_deals = get_all_active_deals()
    deal_to_kill = None

    # Find deal in this group for the target user
    for deal_id, deal_data in active_deals.items():
        if deal_data['group_id'] == group_id and (
            deal_data['buyer'] == target_user or 
            deal_data['seller'] == target_user or 
            deal_data.get('starter') == target_user
        ):
            deal_to_kill = deal_id
            break

    if deal_to_kill:
        deal_data = active_deals[deal_to_kill]
        
        try:
            notification_text = "⚠️ This deal has been forcefully ended by an admin.\n\n"
            
            if deal_data.get('buyer'):
                buyer = await context.bot.get_chat(deal_data['buyer'])
                notification_text += f"Buyer: {buyer.first_name}\n"
                context.user_data.clear()
                context.user_data["state"] = None
                context.user_data.pop('buyer', None)
                
                
            if deal_data.get('seller'):
                seller = await context.bot.get_chat(deal_data['seller'])
                notification_text += f"Seller: {seller.first_name}\n"
                context.user_data.clear()
                context.user_data["state"] = None
                context.user_data.pop('seller', None)
                


            if deal_data.get('amount'):
                notification_text += f"Amount: ${deal_data['amount']:.2f}\n"
                
            notification_text += "\nIf you have any questions, please contact support."
            
            remove_active_deal(deal_to_kill)
            await update.message.reply_text("Deal has been forcefully ended.")
            await context.bot.send_message(
                chat_id=group_id,
                text=notification_text,
                parse_mode='HTML'
            )
            
        except BadRequest as e:
            remove_active_deal(deal_to_kill)
            await update.message.reply_text("Deal terminated. Could not fetch all participant details.")
    else:
        await update.message.reply_text("No active deal found for this user in this group.")




async def handle_killall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
        
    active_deals = get_all_active_deals()
    for deal_id, deal_data in active_deals.items():
        
        if 'buyer' in deal_data:
            context.user_data.clear()
            context.user_data["state"] = None
            context.user_data.pop('buyer', None)
            
       
        if 'seller' in deal_data:
            context.user_data.clear()
            context.user_data["state"] = None
            context.user_data.pop('seller', None)
            
        remove_active_deal(deal_id)
    
    await update.message.reply_text("✅ All active deals have been terminated and user contexts cleared.")

async def send_withdrawal_update_to_seller(bot, seller_id, status, amount, currency):
    
    
    status_messages = {
        "Processing": "Your withdrawal request has been received and is being processed.",
        "Confirming": "Your withdrawal is being confirmed on the blockchain.",
        "Complete": "Your withdrawal has been successfully processed and sent to your wallet.",
        "Expired": "Your withdrawal request has expired. Please contact support for assistance.",
        "Rejected": "Your withdrawal request has been rejected."
    }
    
    message = f"Withdrawal Update:\n\n"
    message += f"Status: {status}\n"
    message += f"Amount: {amount} {currency}\n\n"
    message += status_messages.get(status, "An update has been received for your withdrawal.")
    
    if status == "Complete":
        keyboard = [[InlineKeyboardButton("Completed ✅", callback_data="seller_confirm_paid")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await bot.send_message(chat_id=seller_id, text=message, reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=seller_id, text=message)



async def handle_getdeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command can only be used in a group.")
        return

    group_id = update.effective_chat.id
    active_deals = get_all_active_deals()
    deal_id = None
    
    for d_id, deal in active_deals.items():
        if deal['group_id'] == group_id:
            deal_id = d_id
            deal_data = deal
            break
    
    if not deal_id:
        await update.message.reply_text("No active deal found in this group.")
        return
    
    if deal_data['status'] == 'completed':
        remove_active_deal(deal_id)
        await update.message.reply_text("The deal in this group was completed ✅\n\n Removed from active deals.")
        return
    if deal_data['status'] == 'initiated':
        if deal_data['buyer'] and deal_data['seller']:
            buyer = await context.bot.get_chat(deal_data['buyer'])
            seller = await context.bot.get_chat(deal_data['seller'])
            keyboard = [
                [InlineKeyboardButton("P2P Trade", callback_data="p2p"),
                InlineKeyboardButton("Buy & Sell", callback_data="b_and_s")],
                [InlineKeyboardButton("Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"<b>𝗙𝗟𝗨𝗫𝗫 𝗘𝗦𝗖𝗥𝗢𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘</b>\n\n"
                f"Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
                f"Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>\n\n"
                f"𝗕𝘂𝘆𝗲𝗿, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗰𝗵𝗼𝗼𝘀𝗲 𝘁𝗵𝗲 𝘁𝘆𝗽𝗲 𝗼𝗳 𝗱𝗲𝗮𝗹:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            keyboard = [
                [InlineKeyboardButton("Buyer", callback_data="buyer"),
                 InlineKeyboardButton("Seller", callback_data="seller")],
                [InlineKeyboardButton("Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                format_text("FLUXX ESCROW SERVICE\n\nPlease select your role:", "italic"),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    elif deal_data['status'] == 'deposited' and deal_data['buyer'] and deal_data['seller'] and deal_data['amount']:
        from handlers import calculate_fee
        amount = deal_data['amount']
        fee = calculate_fee(amount, deal_data['deal_type'])
        total = amount + fee
        buyer = await context.bot.get_chat(deal_data['buyer'])
        seller = await context.bot.get_chat(deal_data['seller'])

        keyboard = [  
                [InlineKeyboardButton("💰 Release Payment", callback_data="release_payment")],  
                [InlineKeyboardButton("⏳ Check Timer", callback_data="check_timer")],  
                [InlineKeyboardButton("👨‍💼 Involve Moderator", callback_data="mod")],  
                [InlineKeyboardButton("🚫 End Deal", callback_data="back")]  
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"<b>⚠️ FLUXX ESCROW BOT - PAYMENT CONFIRMED ✅</b>\n\n"
            f"💵 Deposit Amount: ${amount:.2f}\n"
            f"✅ Payment confirmed from <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
            f"🔄 Escrow Fee: ${fee:.2f}\n"
            f"💰 Total: ${total:.2f}\n\n"
            f"⚠️ IMPORTANT INSTRUCTIONS:\n"
            f"1. Complete your deal/transaction first\n"
            f"2. Buyer MUST verify everything is correct\n"
            f"3. <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>, Only click 'Release Payment' after full satisfaction\n"
            f"4. If ANY issues arise, click 'Involve Moderator' immediately\n\n"
            f"🚫 <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>, DO NOT RELEASE PAYMENT BEFORE DEAL COMPLETION\n"
            f"❗️ Any disagreements or scam attempts will be investigated\n\n"
            f"👥 Participants:\n"
            f"Buyer: <a href='tg://user?id={deal_data['buyer']}'>{buyer.first_name}</a>\n"
            f"Seller: <a href='tg://user?id={deal_data['seller']}'>{seller.first_name}</a>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )




async def handle_help_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton("Back 🏠", callback_data="mainmenu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    help_texts = {
        'en': """
🔰 *How to use FLUXX Escrow:*

1️⃣ *Start a Deal:*
- Click "Start Deal"
- Enter deal amount
- Choose deal type

2️⃣ *For Buyers:*
- Send payment within time limit
- Verify received goods/services
- Release payment when satisfied

3️⃣ *For Sellers:*
- Wait for buyer's payment
- Deliver goods/services
- Receive payment after buyer confirms

⚠️ *Safety Tips:*
- Always verify transaction details
- Report Scam to Moderator
- Contact mod if issues arise
        """,
        'hi': """
🔰 *FLUXX Escrow ka upyog kaise karein:*

1️⃣ *Deal shuru karein:*
- "Start Deal" par click karein
- Rashi darj karein
- Deal prakar chunen

2️⃣ *Kharidaron ke liye:*
- Samay seema mein bhugtaan karein
- Praapt samaan/sevayon ki jaanch karein
- Santusht hone par bhugtaan jari karein

3️⃣ *Vikretaon ke liye:*
- Kharidar ke bhugtaan ki pratiksha karein
- Samaan/sevayein deliver karein
- Kharidar ki pushti ke baad bhugtaan praapt karein

⚠️ *Suraksha tips:*
- Hamesha len-den vivaran satyapit karein
- Agar aapko scam ka ahsas ho, to moderator ko report karein
- Samasya hone par mod se sampark karein
        """
    }
    
    await query.edit_message_text(
        help_texts.get(lang, "Language not supported"),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )