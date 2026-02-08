from datetime import datetime, timedelta

from app.client.engsel import get_transaction_history, get_pending_transaction
from app.menus.util import clear_screen

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
        print("0. Refresh")
        print("00. Kembali ke Menu Utama")
        choice = input("Pilih opsi: ")
        if choice == "0":
            continue
        elif choice == "00":
            in_transaction_menu = False
        else:
            print("Opsi tidak valid. Silakan coba lagi.")
