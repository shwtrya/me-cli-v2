# MYnyak Engsel Sunset

![banner](bnr.png)

CLI client for a certain Indonesian mobile internet service provider.

## ✨ Highlights
- Simple, interactive CLI workflow.
- Supports login, package browsing, purchases, and history.
- Optional config file for defaults and styling.

## ✅ Prerequisites
- Python 3.10+ (recommended).
- Internet connection.
- Environment variables from the official channel.
- Optional: install the secure extra to encrypt tokens at rest.

> Trade-off: installing the secure extra adds native crypto dependencies (slower installs),
> but keeps refresh tokens encrypted on disk. Skipping it makes installation faster
> and lighter, but tokens are stored in plaintext.

## 🔐 Environment Variables
1. Open [OUR TELEGRAM CHANNEL](https://t.me/alyxcli).
2. Copy the provided environment variables.
3. Paste them into a `.env` file in the same directory as `main.py`.

> Tip: You can use any text editor, for example `nano .env`.

## 🚀 Quick Start (Linux/macOS)
```bash
bash setup.sh
python main.py
```

### 🔐 Optional secure install (token encryption)
```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-secure.txt
```

If this project is installed as a package, the secure extra can be enabled with:
```bash
python -m pip install ".[secure]"
```

## 📱 Termux Setup (Android)
1. Update & upgrade Termux:
   ```bash
   pkg update && pkg upgrade -y
   ```
2. Install Git:
   ```bash
   pkg install git -y
   ```
3. Clone this repo:
   ```bash
   git clone https://github.com/shwtrya/me-cli-v2
   ```
4. Open the folder:
   ```bash
   cd me-cli-v2
   ```
5. Setup dependencies:
   ```bash
   bash setup.sh
   ```
   Optional (token encryption):
   ```bash
   python -m pip install -r requirements-secure.txt
   ```
6. Run the script:
   ```bash
   python main.py
   ```

## 🧭 Usage Notes
- Keep your `.env` file private.
- If you encounter issues with tokens or sessions, re-run the login flow from the menu.
- Configuration can be adjusted from the app menu (e.g. table width, delay).

## ℹ️ Info
### PS for Certain Indonesian mobile internet service provider
Instead of just delisting the package from the app, ensure the user cannot purchase it.
What's the point of strong client side security when the server don't enforce it?

### Terms of Service
By using this tool, the user agrees to comply with all applicable laws and regulations and to release the developer from any and all claims arising from its use.

### Contact
contact@mashu.lol
