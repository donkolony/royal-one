"""Print a signed access token for a demo user. Works ONLY with AUTH_MODE=local_hs256 (offline development).
  python scripts/make_token.py client1@demo.example
With Supabase, sign in through Supabase Auth to get a real token instead.
"""
import sys

import _bootstrap  # noqa: F401

from app import seed
from app.core.auth import make_test_token
from app.core.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    if s.auth_mode != "local_hs256" or not s.supabase_jwt_secret:
        raise SystemExit("Set AUTH_MODE=local_hs256 and SUPABASE_JWT_SECRET in backend/.env first.")
    email = sys.argv[1] if len(sys.argv) > 1 else "client1@demo.example"
    user = next((u for u in seed.USERS if u["email"] == email), None)
    if user is None:
        raise SystemExit("Unknown demo user. Choose one of: " + ", ".join(u["email"] for u in seed.USERS))
    print(make_test_token(s.supabase_jwt_secret, str(user["id"]), expires_in=8 * 3600))
