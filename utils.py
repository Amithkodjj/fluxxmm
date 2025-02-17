import json
import uuid
from datetime import datetime
from config import P2P_FEE, BS_FEE

def generate_deal_id(buyer_id, seller_id, group_id):
    return f"{buyer_id}{seller_id}{group_id}{uuid.uuid4().hex[:8]}"

def generate_order_id():
    return f"ORDER-{uuid.uuid4().hex[:12].upper()}"

def save_trade(buyer, seller, amount, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trade_data = {
        "timestamp": timestamp,
        "buyer_id": buyer,
        "seller_id": seller,
        "amount_usd": f"{amount:.2f}",
        "status": status,
        "trade_id": generate_order_id()
    }
    
    formatted_trade = (
        f"[{timestamp}] Trade #{trade_data['trade_id']}\n"
        f"├── Amount: ${trade_data['amount_usd']}\n"
        f"├── Buyer ID: {trade_data['buyer_id']}\n"
        f"├── Seller ID: {trade_data['seller_id']}\n"
        f"└── Status: {trade_data['status'].upper()}\n\n"
    )
    
    with open("trades.txt", "a", encoding='utf-8') as f:
        f.write(formatted_trade)


def format_text(text, style):
    # Maps for different font styles
    bold_map = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                            "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇")
    
    italic_map = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                              "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻")
    
    script_map = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                              "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃")
    
    double_struck_map = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                                     "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫")
    
    code_map = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                            "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣")

    style_maps = {
        "bold": bold_map,
        "italic": italic_map,
        "script": script_map,
        "double_struck": double_struck_map,
        "code": code_map
    }

    if style in style_maps:
        return text.translate(style_maps[style])
    return text

def save_active_deal(deal_id, deal_data):
    try:
        with open('active_deals.json', 'r') as f:
            deals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        deals = {}
    
    deals[deal_id] = deal_data
    
    with open('active_deals.json', 'w') as f:
        json.dump(deals, f, indent=4)


def get_active_deal(deal_id):
    try:
        with open("active_deals.json", "r") as f:
            active_deals = json.load(f)
        return active_deals.get(deal_id)
    except FileNotFoundError:
        return None

def update_active_deal(deal_id, updated_data):
    try:
        # Load the existing deals
        with open("active_deals.json", "r") as f:
            active_deals = json.load(f)
        
        if deal_id in active_deals:
            active_deals[deal_id].update(updated_data)
            
            if not isinstance(active_deals, dict):
                raise ValueError("Invalid JSON structure: Root should be a dictionary.")
            if not isinstance(active_deals[deal_id], dict):
                raise ValueError(f"Invalid JSON structure for deal ID {deal_id}: Should be a dictionary.")
            
            with open("active_deals.json", "w") as f:
                json.dump(active_deals, f, indent=4) 
            return True
        else:
            return False
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    except ValueError as e:
        print(f"Error: {e}")
        return False

def remove_active_deal(deal_id):
    try:
        with open("active_deals.json", "r") as f:
            active_deals = json.load(f)
        
        if deal_id in active_deals:
            del active_deals[deal_id]
            
            with open("active_deals.json", "w") as f:
                json.dump(active_deals, f)
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def get_all_active_deals():
    try:
        with open("active_deals.json", "r") as f:
            active_deals = json.load(f)
        return active_deals
    except FileNotFoundError:
        return {}
