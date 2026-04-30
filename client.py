import requests


BASE_URL = "http://127.0.0.1:8000"


def send_message(content: str) -> str:
    response = requests.post(
        f"{BASE_URL}/generate",
        json={"content": content},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    return data.get("response", "")


def main() -> None:
    print("Enter a line for Soma. Type 'exit' to quit.")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        try:
            reply = send_message(user_input)
        except requests.RequestException as exc:
            print(f"Error: {exc}")
            continue

        print(f"Soma: {reply}\n")


if __name__ == "__main__":
    main()