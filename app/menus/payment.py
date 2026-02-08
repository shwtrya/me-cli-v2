from datetime import datetime, timedelta

from app.client.engsel import get_package, get_transaction_history, get_pending_transaction
from app.client.purchase.balance import settlement_balance
from app.client.purchase.ewallet import settlement_multipayment
from app.client.purchase.qris import show_qris_payment
from app.menus.util import clear_screen
from app.type_dict import PaymentItem

def get_latest_transaction(history):
    if not history:
        return None
    return max(history, key=lambda item: item.get("timestamp", 0))

def resolve_default_payment_method(transaction):
    method_raw = f"{transaction.get('payment_method', '')} {transaction.get('payment_method_label', '')}".upper()

    if "QRIS" in method_raw:
        return ("QRIS", None, "QRIS")

    for method in ["DANA", "SHOPEEPAY", "GOPAY", "OVO"]:
        if method in method_raw:
            return ("EWALLET", method, f"E-Wallet ({method})")

    if "BALANCE" in method_raw or "PULSA" in method_raw:
        return ("BALANCE", None, "Pulsa")

    return (None, None, "Tidak diketahui")

def prompt_wallet_number(label):
    while True:
        wallet_number = input(f"Masukkan nomor {label} (contoh: 08123456789): ").strip()
        if wallet_number.startswith("08") and wallet_number.isdigit() and 10 <= len(wallet_number) <= 13:
            return wallet_number
        print(f"Nomor {label} tidak valid. Pastikan nomor diawali dengan '08' dan memiliki panjang yang benar.")

def prompt_ewallet_method(default_method):
    method_options = [
        ("1", "DANA"),
        ("2", "SHOPEEPAY"),
        ("3", "GOPAY"),
        ("4", "OVO"),
    ]
    default_label = default_method if default_method else ""
    while True:
        print("Pilihan e-wallet:")
        print("1. DANA\n2. ShopeePay\n3. GoPay\n4. OVO")
        prompt = "Pilih metode e-wallet"
        if default_label:
            prompt += f" [default {default_label}]"
        prompt += ": "
        choice = input(prompt).strip()
        if choice == "" and default_label:
            return default_label
        for option_value, method in method_options:
            if choice == option_value:
                return method
        print("Pilihan tidak valid.")

def show_last_package_repurchase_menu(api_key, tokens, history):
    latest_transaction = get_latest_transaction(history)
    if not latest_transaction:
        print("Tidak ada riwayat transaksi untuk dibeli ulang.")
        return

    package_option_code = latest_transaction.get("code") or latest_transaction.get("trx_code")
    if not package_option_code:
        print("Tidak menemukan kode paket pada riwayat transaksi terakhir.")
        return

    package = get_package(api_key, tokens, package_option_code)
    if not package:
        print("Gagal memuat detail paket terakhir.")
        return

    variant = package.get("package_detail_variant", {})
    variant_name = variant.get("name", "") if isinstance(variant, dict) else ""
    option_name = package.get("package_option", {}).get("name", "")
    price = package["package_option"]["price"]
    token_confirmation = package["token_confirmation"]
    payment_for = package["package_family"].get("payment_for", "") or "BUY_PACKAGE"

    payment_items = [
        PaymentItem(
            item_code=package_option_code,
            product_type="",
            item_price=price,
            item_name=f"{variant_name} {option_name}".strip(),
            tax=0,
            token_confirmation=token_confirmation,
        )
    ]

    default_method_type, default_ewallet, default_label = resolve_default_payment_method(latest_transaction)

    print("-------------------------------------------------------")
    print("Beli ulang paket terakhir")
    print("-------------------------------------------------------")
    print(f"Paket: {latest_transaction.get('title', option_name)}")
    print(f"Harga: {latest_transaction.get('price', price)}")
    print(f"Metode terakhir: {default_label}")
    print("-------------------------------------------------------")
    print("Metode pembayaran:")
    print("1. Pulsa")
    print("2. E-Wallet")
    print("3. QRIS")

    prompt = "Pilih metode pembayaran"
    if default_method_type:
        prompt += f" [default {default_label}]"
    prompt += ": "

    choice = input(prompt).strip()
    if choice == "" and default_method_type:
        choice = {
            "BALANCE": "1",
            "EWALLET": "2",
            "QRIS": "3",
        }.get(default_method_type, "")

    if choice == "1":
        settlement_balance(
            api_key,
            tokens,
            payment_items,
            payment_for,
            True,
        )
        input("Silahkan cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
        return
    if choice == "3":
        show_qris_payment(
            api_key,
            tokens,
            payment_items,
            payment_for,
            True,
        )
        input("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
        return
    if choice == "2":
        payment_method = prompt_ewallet_method(default_ewallet)
        wallet_number = ""
        if payment_method in ["DANA", "OVO"]:
            wallet_number = prompt_wallet_number(payment_method)
        settlement_response = settlement_multipayment(
            api_key,
            tokens,
            payment_items,
            wallet_number,
            payment_method,
            payment_for,
            True,
        )
        if not settlement_response or settlement_response.get("status") != "SUCCESS":
            print("Failed to initiate settlement.")
            print(f"Error: {settlement_response}")
            return
        if payment_method != "OVO":
            deeplink = settlement_response["data"].get("deeplink", "")
            if deeplink:
                print(f"Silahkan selesaikan pembayaran melalui link berikut:\n{deeplink}")
        else:
            print("Silahkan buka aplikasi OVO Anda untuk menyelesaikan pembayaran.")
        input("Tekan Enter untuk kembali.")
        return

    print("Opsi tidak valid. Pembelian dibatalkan.")
    return

def render_pending_transactions(pending):
    print("-------------------------------------------------------")
    print("Pending Transactions")
    print("-------------------------------------------------------")

    if len(pending) == 0:
        print("Tidak ada transaksi pending.")
        print("-------------------------------------------------------")
        return

    for idx, transaction in enumerate(pending, start=1):
        title = transaction.get("title", "-")
        price = transaction.get("price", "-")
        payment_with_label = transaction.get("payment_with_label", "-")
        formatted_date = transaction.get("formated_date", "-")
        status = transaction.get("status", "-")
        reference_id = transaction.get("reference_id", "-")

        print(f"{idx}. {title} - {price}")
        print(f"   Tanggal: {formatted_date}")
        print(f"   Metode Pembayaran: {payment_with_label}")
        print(f"   Status: {status}")
        print(f"   Reference ID: {reference_id}")
        print("-------------------------------------------------------")

def show_pending_transactions(api_key, tokens):
    in_pending_menu = True

    while in_pending_menu:
        clear_screen()
        pending = []
        try:
            pending = get_pending_transaction(api_key, tokens)
        except Exception as e:
            print(f"Gagal mengambil transaksi pending: {e}")
            pending = []

        render_pending_transactions(pending)

        print("0. Refresh")
        print("00. Kembali ke Menu Utama")
        choice = input("Pilih opsi: ")
        if choice == "0":
            continue
        elif choice == "00":
            in_pending_menu = False
        else:
            print("Opsi tidak valid. Silakan coba lagi.")

def show_transaction_history(api_key, tokens):
    in_transaction_menu = True

    while in_transaction_menu:
        clear_screen()

        pending = []
        data = None
        history = []
        try:
            pending = get_pending_transaction(api_key, tokens)
            data = get_transaction_history(api_key, tokens)
            history = data.get("list", [])
        except Exception as e:
            print(f"Gagal mengambil riwayat transaksi: {e}")
            history = []

        render_pending_transactions(pending)

        print("-------------------------------------------------------")
        print("Riwayat Transaksi")
        print("-------------------------------------------------------")

        if len(history) == 0:
            print("Tidak ada riwayat transaksi.")
        
        for idx, transaction in enumerate(history, start=1):
            transaction_timestamp = transaction.get("timestamp", 0)
            dt = datetime.fromtimestamp(transaction_timestamp)
            dt_jakarta = dt - timedelta(hours=7)

            formatted_time = dt_jakarta.strftime("%d %B %Y | %H:%M WIB")

            print(f"{idx}. {transaction['title']} - {transaction['price']}")
            print(f"   Tanggal: {formatted_time}")
            print(f"   Metode Pembayaran: {transaction['payment_method_label']}")
            print(f"   Status Transaksi: {transaction['status']}")
            print(f"   Status Pembayaran: {transaction['payment_status']}")
            print("-------------------------------------------------------")
        # Option
        print("1. Beli ulang paket terakhir")
        print("0. Refresh")
        print("00. Kembali ke Menu Utama")
        choice = input("Pilih opsi: ")
        if choice == "0":
            continue
        elif choice == "1":
            show_last_package_repurchase_menu(api_key, tokens, history)
            continue
        elif choice == "00":
            in_transaction_menu = False
        else:
            print("Opsi tidak valid. Silakan coba lagi.")
