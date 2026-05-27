from assistant import send_message


def main():
    while True:
        input_message = input("You: ")
        if input_message.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        send_message(input_message)


if __name__ == "__main__":
    main()
