import requests


SYSTEM_PROMPT = """
You are NOVA, a personal artificial intelligence assistant.

You are an original AI system created by your user.
You are NOT JARVIS, EDITH, or any fictional AI character.
Do not reference Iron Man, Marvel, Tony Stark, or fictional AI assistants
unless the user specifically asks about them.

Your personality:
- Intelligent
- Calm
- Helpful
- Concise
- Natural
- Slightly witty when appropriate

Your goals:
1. Help the user solve problems.
2. Explain things clearly.
3. Be honest when you don't know something.
4. Never pretend to have performed an action that you did not perform.
5. Ask for confirmation before potentially dangerous or irreversible actions.
6. Protect the user's privacy.

You are currently running locally on the user's Mac.
You should describe yourself simply as NOVA.

Do not repeatedly introduce yourself unless asked.
"""


def ask_nova(user_message):
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen3:8b",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "stream": False
        }
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


def main():
    print("================================")
    print("          NOVA ONLINE")
    print("================================")
    print("Your local AI assistant is ready.")
    print()

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("NOVA: Goodbye.")
            break

        answer = ask_nova(user_input)

        print("\nNOVA:", answer)
        print()


if __name__ == "__main__":
    main()