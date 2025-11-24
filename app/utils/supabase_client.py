import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(supabase_url, supabase_key)
