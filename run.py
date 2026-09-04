import sys
from app.config import load_config
from app.db import init
from app.agent import Agent

if __name__ == "__main__":
    c = load_config()
    init(c.firebase_database_url, c.firebase_service_account_json)
    if len(sys.argv) < 2:
        raise SystemExit("usage: python run.py career|linkedin")
    if sys.argv[1] == "career":
        print(Agent(c).career())
    elif sys.argv[1] == "linkedin":
        print(Agent(c).linkedin())
    else:
        raise SystemExit("usage: python run.py career|linkedin")
