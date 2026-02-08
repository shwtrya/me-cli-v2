from app.menus.util import clear_screen
from app.client.engsel import (
    get_notification_detail,
    get_notifications,
    mark_notification_read
)
from app.service.auth import AuthInstance

WIDTH = 55

def show_notification_menu():
    in_notification_menu = True
    show_unread_only = False
    while in_notification_menu:
        clear_screen()
        print("Fetching notifications...")
        
        api_key = AuthInstance.api_key
        tokens = AuthInstance.get_active_tokens()
        
        notifications_res = get_notifications(api_key, tokens)
        if not notifications_res:
            print("No notifications found.")
            return
        
        notifications_data = notifications_res.get("data", {})
        if isinstance(notifications_data, list):
            notifications = notifications_data
        elif isinstance(notifications_data, dict):
            notifications = (
                notifications_data.get("data")
                or notifications_data.get("notifications")
                or notifications_data.get("notification")
                or []
            )
            if isinstance(notifications, dict):
                notifications = notifications.get("data", [])
        else:
            notifications = []
        if not notifications:
            print("No notifications available.")
            return
        
        filtered_notifications = [
            notification for notification in notifications
            if not show_unread_only or not notification.get("is_read", False)
        ]

        print("=" * WIDTH)
        print("Notifications:")
        print("=" * WIDTH)
        unread_count = 0
        for idx, notification in enumerate(filtered_notifications):
            is_read = notification.get("is_read", False)
            full_message = notification.get("full_message", "")
            brief_message = notification.get("brief_message", "")
            time = notification.get("timestamp", "")
            
            status = ""
            if is_read:
                status = "READ"
            else:
                status = "UNREAD"
                unread_count += 1

            print(f"{idx + 1}. [{status}] {brief_message}")
            print(f"- Time: {time}")
            print(f"- {full_message}")
            print("-" * WIDTH)
        print(f"Total notifications: {len(notifications)} | Unread: {unread_count}")
        print("=" * WIDTH)
        print("1. Read All Unread Notifications")
        print(f"2. Toggle Filter Unread Only ({'ON' if show_unread_only else 'OFF'})")
        print("00. Back to Main Menu")
        print("=" * WIDTH)
        choice = input("Enter your choice: ")
        if choice == "1":
            unread_notifications = [
                notification for notification in notifications
                if not notification.get("is_read", False)
            ]
            if not unread_notifications:
                print("No unread notifications to mark as read.")
                input("Press Enter to return to the notification menu...")
                continue
            for notification in unread_notifications:
                notification_id = notification.get("notification_id")
                if not notification_id:
                    continue
                if not mark_notification_read(api_key, tokens, notification_id):
                    detail = get_notification_detail(api_key, tokens, notification_id)
                    if detail:
                        print(f"Mark as READ notification ID: {notification_id}")
                else:
                    print(f"Mark as READ notification ID: {notification_id}")
            input("Press Enter to return to the notification menu...")
        elif choice == "2":
            show_unread_only = not show_unread_only
        elif choice == "00":
            in_notification_menu = False
        else:
            print("Invalid choice. Please try again.")
