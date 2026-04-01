from __future__ import annotations

from app.chatbot.router import route
from app.config import get_config
from app.db.init_db import initialize_database


def main() -> None:
    """
    Application entrypoint.
    """
    config = get_config()
    initialize_database(config.DB_PATH)

    print("Welcome to Central Parking Wroclaw Assistant.")
    print(
        "I can provide parking information, help you create a reservation request, "
        "or cancel an upcoming reservation."
    )
    print("Type 'exit' to quit.")

    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
    }

    while True:
        query = input("You: ").strip()

        if not query:
            print("Bot: Please enter a message.")
            continue

        if query.lower() == "exit":
            print("Bot: Goodbye.")
            break

        response = route(query, session)
        print(f"Bot: {response}")


if __name__ == "__main__":
    main()