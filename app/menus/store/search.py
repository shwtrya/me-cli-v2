import re

from app.client.store.search import get_family_list, get_store_packages
from app.menus.package import get_packages_by_family, show_package_details
from app.menus.util import clear_screen, pause
from app.service.auth import AuthInstance

WIDTH = 55

QUOTA_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024 ** 2,
    "GB": 1024 ** 3,
    "TB": 1024 ** 4,
}

VALIDITY_UNITS = {
    "d": 1,
    "day": 1,
    "days": 1,
    "m": 30,
    "mo": 30,
    "month": 30,
    "months": 30,
    "y": 365,
    "yr": 365,
    "year": 365,
    "years": 365,
}

QUOTA_FIELDS = (
    "quota_bytes",
    "quota_byte",
    "quota",
    "main_quota",
    "total_quota",
    "quota_total",
    "data_quota",
    "quota_gb",
    "quota_mb",
    "quota_kb",
)

TEXT_FIELDS = (
    "title",
    "description",
    "short_description",
    "benefit_description",
    "detail",
    "benefits",
)


def parse_price_range(value: str):
    cleaned = value.replace(" ", "")
    if not cleaned:
        return None, None
    if "-" in cleaned:
        min_str, max_str = cleaned.split("-", 1)
    else:
        min_str, max_str = cleaned, ""
    min_price = int(min_str) if min_str else None
    max_price = int(max_str) if max_str else None
    return min_price, max_price


def parse_quota_bytes_from_text(text: str):
    if not text:
        return None
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(TB|GB|MB|KB|B)\b", text, re.IGNORECASE)
    if not matches:
        return None
    best_bytes = None
    for number, unit in matches:
        normalized = number.replace(",", ".")
        amount = float(normalized)
        multiplier = QUOTA_UNITS.get(unit.upper(), 1)
        bytes_value = int(amount * multiplier)
        if best_bytes is None or bytes_value > best_bytes:
            best_bytes = bytes_value
    return best_bytes


def extract_quota_bytes(package: dict):
    for field in QUOTA_FIELDS:
        value = package.get(field)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            if field.endswith("_gb"):
                return int(value * QUOTA_UNITS["GB"])
            if field.endswith("_mb"):
                return int(value * QUOTA_UNITS["MB"])
            if field.endswith("_kb"):
                return int(value * QUOTA_UNITS["KB"])
            return int(value)
        if isinstance(value, str):
            parsed = parse_quota_bytes_from_text(value)
            if parsed is not None:
                return parsed
    text_parts = []
    for field in TEXT_FIELDS:
        value = package.get(field)
        if isinstance(value, list):
            text_parts.extend([str(item) for item in value])
        elif value:
            text_parts.append(str(value))
    return parse_quota_bytes_from_text(" ".join(text_parts))


def parse_validity_days(validity_text: str):
    if not validity_text:
        return None
    matches = re.findall(r"(\d+)\s*([a-zA-Z]+)", validity_text.lower())
    if not matches:
        return None
    best_days = None
    for amount_str, unit in matches:
        multiplier = VALIDITY_UNITS.get(unit)
        if multiplier is None:
            continue
        days = int(amount_str) * multiplier
        if best_days is None or days > best_days:
            best_days = days
    return best_days


def get_package_price(package: dict):
    original_price = package.get("original_price", 0) or 0
    discounted_price = package.get("discounted_price", 0) or 0
    return discounted_price if discounted_price > 0 else original_price


def filter_store_packages(store_packages: list, price_min, price_max, quota_min_bytes, validity_min_days):
    filtered = []
    for package in store_packages:
        price = get_package_price(package)
        if price_min is not None and price < price_min:
            continue
        if price_max is not None and price > price_max:
            continue
        if quota_min_bytes is not None:
            quota_bytes = extract_quota_bytes(package)
            if quota_bytes is None or quota_bytes < quota_min_bytes:
                continue
        if validity_min_days is not None:
            validity_days = parse_validity_days(str(package.get("validity", "")))
            if validity_days is None or validity_days < validity_min_days:
                continue
        filtered.append(package)
    return filtered

def show_family_list_menu(
    subs_type: str = "PREPAID",
    is_enterprise: bool = False,
):
    in_family_list_menu = True
    while in_family_list_menu:
        api_key = AuthInstance.api_key
        tokens = AuthInstance.get_active_tokens()
        
        print("Fetching family list...")
        family_list_res = get_family_list(api_key, tokens, subs_type, is_enterprise)
        if not family_list_res:
            print("No family list found.")
            in_family_list_menu = False
            continue
        
        family_list = family_list_res.get("data", {}).get("results", [])
        
        clear_screen()
        
        print("=" * WIDTH)
        print("Family List:")
        print("=" * WIDTH)
        
        for i, family in enumerate(family_list):
            family_name = family.get("label", "N/A")
            family_code = family.get("id", "N/A")
            
            print(f"{i + 1}. {family_name}")
            print(f"   Family code: {family_code}")
            print("-" * WIDTH)
        
        print("00. Back to Main Menu")
        print("Input the number to view packages in that family.")
        choice = input("Enter your choice: ")
        if choice == "00":
            in_family_list_menu = False
        
        if choice.isdigit() and int(choice) > 0 and int(choice) <= len(family_list):
            selected_family = family_list[int(choice) - 1]
            family_code = selected_family.get("id", "")
            family_name = selected_family.get("label", "N/A")
            
            print(f"Fetching packages for family: {family_name}...")
            get_packages_by_family(family_code)
    
    pause()

def show_store_packages_menu(
    subs_type: str = "PREPAID",
    is_enterprise: bool = False,
):
    in_store_packages_menu = True
    while in_store_packages_menu:
        api_key = AuthInstance.api_key
        tokens = AuthInstance.get_active_tokens()
        
        print("Fetching store packages...")
        store_packages_res = get_store_packages(api_key, tokens, subs_type, is_enterprise)
        if not store_packages_res:
            print("No store packages found.")
            in_store_packages_menu = False
            continue
        
        store_packages = store_packages_res.get("data", {}).get("results_price_only", [])
        filter_choice = input("Filter results? (y/N): ").strip().lower()
        if filter_choice == "y":
            price_range_input = input("Range harga (min-max, kosongkan untuk skip): ").strip()
            quota_input = input("Minimal kuota (contoh 5GB/1024MB, kosongkan skip): ").strip()
            validity_input = input("Minimal masa aktif (hari, kosongkan skip): ").strip()

            try:
                price_min, price_max = parse_price_range(price_range_input)
            except ValueError:
                print("Format range harga tidak valid, filter harga dilewati.")
                price_min, price_max = None, None

            quota_min_bytes = None
            if quota_input:
                quota_min_bytes = parse_quota_bytes_from_text(quota_input)
                if quota_min_bytes is None:
                    print("Format kuota tidak valid, filter kuota dilewati.")

            validity_min_days = None
            if validity_input:
                if validity_input.isdigit():
                    validity_min_days = int(validity_input)
                else:
                    print("Format masa aktif tidak valid, filter masa aktif dilewati.")

            store_packages = filter_store_packages(
                store_packages,
                price_min,
                price_max,
                quota_min_bytes,
                validity_min_days,
            )

        if not store_packages:
            print("No store packages match the selected filters.")
            pause()
            continue

        clear_screen()
        
        print("=" * WIDTH)
        print("Store Packages:")
        print("=" * WIDTH)
        
        packages = {}
        for i, package in enumerate(store_packages):
            title = package.get("title", "N/A")

            price = get_package_price(package)
            validity = package.get("validity", "N/A")
            family_name = package.get("family_name", "N/A")
            
            action_type = package.get("action_type", "")
            action_param = package.get("action_param", "")
            
            packages[f"{i + 1}"] = {
                "action_type": action_type,
                "action_param": action_param
            }
            
            print(f"{i + 1}. {title}")
            print(f"   Family: {family_name}")
            print(f"   Price: Rp{price}")
            print(f"   Validity: {validity}")
            print("-" * WIDTH)
        
        print("00. Back to Main Menu")
        print("Input the number to view package details.")
        choice = input("Enter your choice: ")
        if choice == "00":
            in_store_packages_menu = False
        elif choice in packages:
            selected_package = packages[choice]
            
            action_type = selected_package["action_type"]
            action_param = selected_package["action_param"]
            
            if action_type == "PDP":
                _ = show_package_details(
                        api_key,
                        tokens,
                        action_param,
                        is_enterprise
                    )
            else:
                print("=" * WIDTH)
                print("Unhandled Action Type")
                print(f"Action type: {action_type}\nParam: {action_param}")
                pause()
        else:
            print("Invalid choice. Please enter a valid package number.")
            pause()
