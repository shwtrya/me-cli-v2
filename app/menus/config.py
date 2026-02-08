from app.menus.util import clear_screen, pause
from app.service.config import apply_config, load_config, prompt_bool, prompt_int, save_config


def show_config_menu() -> dict:
    config = load_config()
    while True:
        clear_screen()
        print("-------------------------------------------------------")
        print("Konfigurasi Aplikasi")
        print("-------------------------------------------------------")
        print(f"1. Default enterprise: {'ON' if config['enterprise_default'] else 'OFF'}")
        print(f"2. NO_COLOR: {'ON' if config['no_color'] else 'OFF'}")
        print(f"3. Lebar tabel: {config['table_width']}")
        print(f"4. Delay loop pembelian (detik): {config['purchase_delay_seconds']}")
        print(f"5. Tampilkan banner: {'ON' if config['show_banner'] else 'OFF'}")
        print("S. Simpan konfigurasi")
        print("00. Kembali")
        print("-------------------------------------------------------")

        choice = input("Pilih menu: ").strip().lower()
        if choice == "1":
            config["enterprise_default"] = prompt_bool(
                "Gunakan default enterprise? (y/n)",
                config["enterprise_default"],
            )
        elif choice == "2":
            config["no_color"] = prompt_bool(
                "Aktifkan NO_COLOR? (y/n)",
                config["no_color"],
            )
        elif choice == "3":
            config["table_width"] = prompt_int(
                "Lebar tabel",
                config["table_width"],
            )
        elif choice == "4":
            config["purchase_delay_seconds"] = prompt_int(
                "Delay loop pembelian (detik)",
                config["purchase_delay_seconds"],
            )
        elif choice == "5":
            config["show_banner"] = prompt_bool(
                "Tampilkan banner ASCII? (y/n)",
                config["show_banner"],
            )
        elif choice == "s":
            save_config(config)
            apply_config(config)
            print("Konfigurasi tersimpan.")
            pause()
        elif choice == "00":
            return config
        else:
            print("Pilihan tidak valid.")
            pause()
