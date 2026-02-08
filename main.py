from dotenv import load_dotenv

from app.service.git import check_for_updates
load_dotenv()

import argparse
import sys, json
from datetime import datetime
from app.menus.util import clear_screen, pause, render_header, format_price, style_text
from app.client.engsel import (
    get_balance,
    get_tiering_info,
)
from app.client.famplan import validate_msisdn
from app.menus.payment import show_transaction_history
from app.service.auth import AuthInstance
from app.menus.bookmark import show_bookmark_menu
from app.menus.account import show_account_menu
from app.menus.package import fetch_my_packages, get_packages_by_family, show_package_details
from app.menus.hot import show_hot_menu, show_hot_menu2
from app.service.sentry import enter_sentry_mode
from app.menus.purchase import purchase_by_family
from app.menus.famplan import show_family_info
from app.menus.circle import show_circle_info
from app.menus.notification import show_notification_menu
from app.menus.store.segments import show_store_segments_menu
from app.menus.store.search import show_family_list_menu, show_store_packages_menu
from app.menus.store.redemables import show_redeemables_menu
from app.client.registration import dukcapil

WIDTH = 55

def show_main_menu(profile):
    clear_screen()
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d")
    balance_text = format_price(profile["balance"])
    header = render_header(
        "MyXL CLI",
        WIDTH,
        subtitle="Menu Utama",
        meta_lines=[
            f"Nomor: {profile['number']} | Type: {profile['subscription_type']}",
            f"Pulsa: {balance_text} | Aktif sampai: {expired_at_dt}",
            profile["point_info"],
        ],
    )
    print(header)
    print(style_text("Menu:", bold=True))
    print("1. Login/Ganti akun")
    print("2. Lihat Paket Saya")
    print("3. Beli Paket 🔥 HOT 🔥")
    print("4. Beli Paket 🔥 HOT-2 🔥")
    print("5. Beli Paket Berdasarkan Option Code")
    print("6. Beli Paket Berdasarkan Family Code")
    print("7. Beli Semua Paket di Family Code (loop)")
    print("8. Riwayat Transaksi")
    print("9. Family Plan/Akrab Organizer")
    print("10. Circle")
    print("11. Store Segments")
    print("12. Store Family List")
    print("13. Store Packages")
    print("14. Redemables")
    print("R. Register")
    print("N. Notifikasi")
    print("V. Validate msisdn")
    print("00. Bookmark Paket")
    print("99. Tutup aplikasi")
    print("-------------------------------------------------------")

show_menu = True

def ensure_active_user():
    active_user = AuthInstance.get_active_user()
    if active_user is None:
        selected_user_number = show_account_menu()
        if selected_user_number:
            AuthInstance.set_active_user(selected_user_number)
            active_user = AuthInstance.get_active_user()
        else:
            print("No user selected or failed to load user.")
    return active_user

def prompt_yes_no(message: str) -> bool:
    answer = input(message).strip().lower()
    return answer == "y"

def run_login_command(args):
    selected_user_number = show_account_menu()
    if selected_user_number:
        AuthInstance.set_active_user(selected_user_number)
    else:
        print("No user selected or failed to load user.")
        return

    if args.msisdn:
        active_user = ensure_active_user()
        if not active_user:
            return
        res = validate_msisdn(
            AuthInstance.api_key,
            active_user["tokens"],
            args.msisdn,
        )
        print(json.dumps(res, indent=2))
        pause()

def run_packages_command(args):
    active_user = ensure_active_user()
    if not active_user:
        return

    if args.option_code:
        show_package_details(
            AuthInstance.api_key,
            active_user["tokens"],
            args.option_code,
            args.enterprise,
        )
        return
    if args.family_code:
        get_packages_by_family(args.family_code)
        return

    fetch_my_packages()

def run_purchase_command(args):
    active_user = ensure_active_user()
    if not active_user:
        return

    if args.option_code:
        show_package_details(
            AuthInstance.api_key,
            active_user["tokens"],
            args.option_code,
            args.enterprise,
        )
        return

    if not args.family_code:
        family_code = input("Enter family code (or '99' to cancel): ")
        if family_code == "99":
            return
    else:
        family_code = args.family_code

    if args.start_from_option is None:
        start_from_option = input("Start purchasing from option number (default 1): ")
        try:
            start_from_option = int(start_from_option)
        except ValueError:
            start_from_option = 1
    else:
        start_from_option = args.start_from_option

    if args.use_decoy is None:
        use_decoy = prompt_yes_no("Use decoy package? (y/n): ")
    else:
        use_decoy = args.use_decoy

    if args.pause_on_success is None:
        pause_on_success = prompt_yes_no("Pause on each successful purchase? (y/n): ")
    else:
        pause_on_success = args.pause_on_success

    if args.delay_seconds is None:
        delay_seconds = input("Delay seconds between purchases (0 for no delay): ")
        try:
            delay_seconds = int(delay_seconds)
        except ValueError:
            delay_seconds = 0
    else:
        delay_seconds = args.delay_seconds

    purchase_by_family(
        family_code,
        use_decoy,
        pause_on_success,
        delay_seconds,
        start_from_option,
    )

def run_history_command(args):
    active_user = ensure_active_user()
    if not active_user:
        return
    show_transaction_history(AuthInstance.api_key, active_user["tokens"])

def run_notifications_command(args):
    active_user = ensure_active_user()
    if not active_user:
        return
    show_notification_menu()

def build_parser():
    parser = argparse.ArgumentParser(description="MyXL CLI")
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="Login atau ganti akun")
    login_parser.add_argument("--msisdn", help="MSISDN untuk divalidasi")
    login_parser.set_defaults(func=run_login_command)

    packages_parser = subparsers.add_parser("packages", help="Kelola paket")
    packages_parser.add_argument("--option-code", help="Option code paket")
    packages_parser.add_argument("--family-code", help="Family code paket")
    packages_parser.add_argument(
        "--enterprise",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Gunakan mode enterprise",
    )
    packages_parser.set_defaults(func=run_packages_command)

    purchase_parser = subparsers.add_parser("purchase", help="Beli paket")
    purchase_parser.add_argument("--option-code", help="Option code paket")
    purchase_parser.add_argument("--family-code", help="Family code paket")
    purchase_parser.add_argument(
        "--enterprise",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Gunakan mode enterprise",
    )
    purchase_parser.add_argument(
        "--use-decoy",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Gunakan paket decoy",
    )
    purchase_parser.add_argument(
        "--pause-on-success",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Pause setiap pembelian sukses",
    )
    purchase_parser.add_argument(
        "--delay-seconds",
        type=int,
        default=None,
        help="Delay antar pembelian (detik)",
    )
    purchase_parser.add_argument(
        "--start-from-option",
        type=int,
        default=None,
        help="Mulai pembelian dari nomor option",
    )
    purchase_parser.set_defaults(func=run_purchase_command)

    history_parser = subparsers.add_parser("history", help="Riwayat transaksi")
    history_parser.set_defaults(func=run_history_command)

    notifications_parser = subparsers.add_parser("notifications", help="Notifikasi")
    notifications_parser.set_defaults(func=run_notifications_command)

    return parser

def run_cli():
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        return False
    args.func(args)
    return True

def main():
    
    while True:
        active_user = AuthInstance.get_active_user()

        # Logged in
        if active_user is not None:
            balance = get_balance(AuthInstance.api_key, active_user["tokens"]["id_token"])
            balance_remaining = balance.get("remaining")
            balance_expired_at = balance.get("expired_at")
            
            point_info = "Points: N/A | Tier: N/A"
            
            if active_user["subscription_type"] == "PREPAID":
                tiering_data = get_tiering_info(AuthInstance.api_key, active_user["tokens"])
                tier = tiering_data.get("tier", 0)
                current_point = tiering_data.get("current_point", 0)
                point_info = f"Points: {current_point} | Tier: {tier}"
            
            profile = {
                "number": active_user["number"],
                "subscriber_id": active_user["subscriber_id"],
                "subscription_type": active_user["subscription_type"],
                "balance": balance_remaining,
                "balance_expired_at": balance_expired_at,
                "point_info": point_info
            }

            show_main_menu(profile)

            choice = input("Pilih menu: ")
            # Testing shortcuts
            if choice.lower() == "t":
                pause()
            elif choice == "1":
                selected_user_number = show_account_menu()
                if selected_user_number:
                    AuthInstance.set_active_user(selected_user_number)
                else:
                    print("No user selected or failed to load user.")
                continue
            elif choice == "2":
                fetch_my_packages()
                continue
            elif choice == "3":
                show_hot_menu()
            elif choice == "4":
                show_hot_menu2()
            elif choice == "5":
                option_code = input("Enter option code (or '99' to cancel): ")
                if option_code == "99":
                    continue
                show_package_details(
                    AuthInstance.api_key,
                    active_user["tokens"],
                    option_code,
                    False
                )
            elif choice == "6":
                family_code = input("Enter family code (or '99' to cancel): ")
                if family_code == "99":
                    continue
                get_packages_by_family(family_code)
            elif choice == "7":
                family_code = input("Enter family code (or '99' to cancel): ")
                if family_code == "99":
                    continue

                start_from_option = input("Start purchasing from option number (default 1): ")
                try:
                    start_from_option = int(start_from_option)
                except ValueError:
                    start_from_option = 1

                use_decoy = input("Use decoy package? (y/n): ").lower() == 'y'
                pause_on_success = input("Pause on each successful purchase? (y/n): ").lower() == 'y'
                delay_seconds = input("Delay seconds between purchases (0 for no delay): ")
                try:
                    delay_seconds = int(delay_seconds)
                except ValueError:
                    delay_seconds = 0
                purchase_by_family(
                    family_code,
                    use_decoy,
                    pause_on_success,
                    delay_seconds,
                    start_from_option
                )
            elif choice == "8":
                show_transaction_history(AuthInstance.api_key, active_user["tokens"])
            elif choice == "9":
                show_family_info(AuthInstance.api_key, active_user["tokens"])
            elif choice == "10":
                show_circle_info(AuthInstance.api_key, active_user["tokens"])
            elif choice == "11":
                input_11 = input("Is enterprise store? (y/n): ").lower()
                is_enterprise = input_11 == 'y'
                show_store_segments_menu(is_enterprise)
            elif choice == "12":
                input_12_1 = input("Is enterprise? (y/n): ").lower()
                is_enterprise = input_12_1 == 'y'
                show_family_list_menu(profile['subscription_type'], is_enterprise)
            elif choice == "13":
                input_13_1 = input("Is enterprise? (y/n): ").lower()
                is_enterprise = input_13_1 == 'y'
                
                show_store_packages_menu(profile['subscription_type'], is_enterprise)
            elif choice == "14":
                input_14_1 = input("Is enterprise? (y/n): ").lower()
                is_enterprise = input_14_1 == 'y'
                
                show_redeemables_menu(is_enterprise)
            elif choice == "00":
                show_bookmark_menu()
            elif choice == "99":
                print("Exiting the application.")
                sys.exit(0)
            elif choice.lower() == "r":
                msisdn = input("Enter msisdn (628xxxx): ")
                nik = input("Enter NIK: ")
                kk = input("Enter KK: ")
                
                res = dukcapil(
                    AuthInstance.api_key,
                    msisdn,
                    kk,
                    nik,
                )
                print(json.dumps(res, indent=2))
                pause()
            elif choice.lower() == "v":
                msisdn = input("Enter the msisdn to validate (628xxxx): ")
                res = validate_msisdn(
                    AuthInstance.api_key,
                    active_user["tokens"],
                    msisdn,
                )
                print(json.dumps(res, indent=2))
                pause()
            elif choice.lower() == "n":
                show_notification_menu()
            elif choice == "s":
                enter_sentry_mode()
            else:
                print("Invalid choice. Please try again.")
                pause()
        else:
            # Not logged in
            selected_user_number = show_account_menu()
            if selected_user_number:
                AuthInstance.set_active_user(selected_user_number)
            else:
                print("No user selected or failed to load user.")

if __name__ == "__main__":
    try:
        print("Checking for updates...")
        need_update = check_for_updates()
        if need_update:
            pause()

        handled = run_cli()
        if not handled:
            main()
    except KeyboardInterrupt:
        print("\nExiting the application.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")
