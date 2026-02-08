import os
import json
import time
from typing import Any
import importlib.util

try:
    from cryptography.fernet import Fernet, InvalidToken
    has_crypto = True
except ImportError:
    Fernet = None
    InvalidToken = Exception
    has_crypto = False

keyring = None
if importlib.util.find_spec("keyring") is not None:
    import keyring

from app.client.ciam import get_new_token
from app.client.engsel import get_profile
from app.util import ensure_api_key

class Auth:
    _instance_ = None
    _initialized_ = False

    api_key = ""

    refresh_tokens = []
    # Format of refresh_tokens:
    # [
        # {
            # "number": int,
            # "subscriber_id": str,
            # "subscription_type": str,
            # "refresh_token": str
        # }
    # ]

    active_user = None
    # {
    #     "number": int,
    #     "subscriber_id": str,
    #     "subscription_type": str,
    #     "tokens": {
    #         "refresh_token": str,
    #         "access_token": str,
    #         "id_token": str
	#     }
    # }
    
    last_refresh_time = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self):
        if not self._initialized_:
            self.api_key = ensure_api_key()

            self.data_dir = os.path.expanduser("~/.myxl-cli")
            self.refresh_tokens_path = os.path.join(self.data_dir, "refresh-tokens.json")
            self.active_number_path = os.path.join(self.data_dir, "active.number")
            self._warned_plaintext_storage = False
            env_encrypt = os.getenv("MYXL_CLI_ENCRYPT_TOKENS", "1") not in {"0", "false", "False"}
            self.encryption_enabled = env_encrypt and has_crypto

            self._ensure_data_dir()
            self._migrate_legacy_files()
            self._warn_if_plaintext_storage()

            if os.path.exists(self.refresh_tokens_path):
                self.load_tokens()
            else:
                self.write_tokens_to_file()

            # Select active user from file if available
            self.load_active_number()
            self.last_refresh_time = int(time.time())

            self._initialized_ = True
            
    def _ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_encryption_key(self) -> bytes:
        if not has_crypto:
            raise RuntimeError("Token encryption requires the optional cryptography dependency.")
        env_key = os.getenv("MYXL_CLI_TOKEN_KEY")
        if env_key:
            return env_key.encode("utf-8")

        if keyring:
            stored = keyring.get_password("myxl-cli", "refresh-tokens")
            if stored:
                return stored.encode("utf-8")
            new_key = Fernet.generate_key()
            keyring.set_password("myxl-cli", "refresh-tokens", new_key.decode("utf-8"))
            return new_key

        key_path = os.path.join(self.data_dir, "token.key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        new_key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(new_key)
        os.chmod(key_path, 0o600)
        return new_key

    def _encrypt_payload(self, payload: str) -> str:
        if not has_crypto:
            raise RuntimeError("Token encryption requires the optional cryptography dependency.")
        fernet = Fernet(self._get_encryption_key())
        return fernet.encrypt(payload.encode("utf-8")).decode("utf-8")

    def _decrypt_payload(self, payload: str) -> str:
        if not has_crypto:
            raise RuntimeError("Token encryption requires the optional cryptography dependency.")
        fernet = Fernet(self._get_encryption_key())
        return fernet.decrypt(payload.encode("utf-8")).decode("utf-8")

    def _warn_if_plaintext_storage(self):
        if self.encryption_enabled or self._warned_plaintext_storage:
            return
        reason = "MYXL_CLI_ENCRYPT_TOKENS=0"
        if not has_crypto:
            reason = "cryptography is not installed"
        print(
            "WARNING: Token encryption is disabled "
            f"({reason}). Tokens will be stored in plaintext. "
            "This speeds up installation but is less secure. "
            "Install the secure extra to enable encryption."
        )
        self._warned_plaintext_storage = True

    def _migrate_legacy_files(self):
        legacy_tokens_path = "refresh-tokens.json"
        legacy_active_path = "active.number"

        if os.path.exists(legacy_tokens_path) and not os.path.exists(self.refresh_tokens_path):
            with open(legacy_tokens_path, "r", encoding="utf-8") as f:
                legacy_tokens = json.load(f)
            self.refresh_tokens = legacy_tokens if isinstance(legacy_tokens, list) else []
            self.write_tokens_to_file()
            os.remove(legacy_tokens_path)

        if os.path.exists(legacy_active_path) and not os.path.exists(self.active_number_path):
            os.replace(legacy_active_path, self.active_number_path)

    def _load_token_payload(self) -> list[dict[str, Any]]:
        with open(self.refresh_tokens_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict) and raw.get("encrypted"):
            if not has_crypto:
                print("Encrypted tokens found but cryptography is not installed.")
                print("Install the secure extra to decrypt stored tokens.")
                return []
            try:
                decrypted = self._decrypt_payload(raw.get("payload", ""))
            except InvalidToken:
                print("Failed to decrypt refresh tokens. Check MYXL_CLI_TOKEN_KEY or keyring.")
                return []
            return json.loads(decrypted)

        if isinstance(raw, list):
            if self.encryption_enabled:
                self.refresh_tokens = raw
                self.write_tokens_to_file()
            return raw

        return []

    def load_tokens(self):
        refresh_tokens = self._load_token_payload()

        if len(refresh_tokens) !=  0:
            self.refresh_tokens = []

        # Validate and load tokens
        for rt in refresh_tokens:
            if "number" in rt and "refresh_token" in rt:
                self.refresh_tokens.append(rt)
            else:
                print(f"Invalid token entry: {rt}")

    def add_refresh_token(self, number: int, refresh_token: str):
        # Check if number already exist, if yes, replace it, if not append
        existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if existing:
            existing["refresh_token"] = refresh_token
        else:
            tokens = get_new_token(self.api_key, refresh_token, "")
            profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
            sub_id = profile_data["profile"]["subscriber_id"]
            sub_type = profile_data["profile"]["subscription_type"]

            self.refresh_tokens.append({
                "number": int(number),
                "subscriber_id": sub_id,
                "subscription_type": sub_type,
                "refresh_token": refresh_token
            })
        
        # Save to file
        self.write_tokens_to_file()

        # Set active user to newly added
        self.set_active_user(number)
            
    def remove_refresh_token(self, number: int):
        self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
        
        # Save to file
        self.write_tokens_to_file()
        
        # If the removed user was the active user, select a new active user if available
        if self.active_user and self.active_user["number"] == number:
            # Select the first user as active user by default
            if len(self.refresh_tokens) != 0:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                if tokens:
                    self.set_active_user(first_rt["number"])
            else:
                input("No users left. Press Enter to continue...")
                self.active_user = None

    def set_active_user(self, number: int):
        # Get refresh token for the number from refresh_tokens
        rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if not rt_entry:
            print(f"No refresh token found for number: {number}")
            input("Press Enter to continue...")
            return False

        tokens = get_new_token(self.api_key, rt_entry["refresh_token"], rt_entry.get("subscriber_id", ""))
        if not tokens:
            print(f"Failed to get tokens for number: {number}. The refresh token might be invalid or expired.")
            input("Press Enter to continue...")
            return False

        profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
        subscriber_id = profile_data["profile"]["subscriber_id"]
        subscription_type = profile_data["profile"]["subscription_type"]

        self.active_user = {
            "number": int(number),
            "subscriber_id": subscriber_id,
            "subscription_type": subscription_type,
            "tokens": tokens
        }
        
        # Update refresh token entry with subscriber_id and subscription_type
        rt_entry["subscriber_id"] = subscriber_id
        rt_entry["subscription_type"] = subscription_type
        
        # Update refresh token. The real client app do this, not sure why cz refresh token should still be valid
        rt_entry["refresh_token"] = tokens["refresh_token"]
        self.write_tokens_to_file()
        
        self.last_refresh_time = int(time.time())
        
        # Save active number to file
        self.write_active_number()

    def renew_active_user_token(self):
        if self.active_user:
            tokens = get_new_token(self.api_key, self.active_user["tokens"]["refresh_token"], self.active_user["subscriber_id"])
            if tokens:
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])
                
                print("Active user token renewed successfully.")
                return True
            else:
                print("Failed to renew active user token.")
                input("Press Enter to continue...")
        else:
            print("No active user set or missing refresh token.")
            input("Press Enter to continue...")
        return False
    
    def get_active_user(self):
        if not self.active_user:
            # Choose the first user if available
            if len(self.refresh_tokens) != 0:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                if tokens:
                    self.set_active_user(first_rt["number"])
                    return self.active_user
            return None
        
        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
            self.last_refresh_time = time.time()
        
        return self.active_user
    
    def get_active_tokens(self) -> dict | None:
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
    def write_tokens_to_file(self):
        if self.encryption_enabled:
            payload = json.dumps(self.refresh_tokens, indent=4)
            encrypted = self._encrypt_payload(payload)
            data = {"encrypted": True, "payload": encrypted}
        else:
            self._warn_if_plaintext_storage()
            data = self.refresh_tokens

        with open(self.refresh_tokens_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    def write_active_number(self):
        if self.active_user:
            with open(self.active_number_path, "w", encoding="utf-8") as f:
                f.write(str(self.active_user["number"]))
        else:
            if os.path.exists(self.active_number_path):
                os.remove(self.active_number_path)
    
    def load_active_number(self):
        if os.path.exists(self.active_number_path):
            with open(self.active_number_path, "r", encoding="utf-8") as f:
                number_str = f.read().strip()
                if number_str.isdigit():
                    number = int(number_str)
                    self.set_active_user(number)

AuthInstance = Auth()
