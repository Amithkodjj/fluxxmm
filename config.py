import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
OXAPAY_API_KEY = os.getenv("OXAPAY_API_KEY")
OXAPAY_PAYOUT_KEY = os.getenv("OXAPAY_PAYOUT_KEY")
P2P_FEE = 0.025  
BS_FEE = 0.03   

