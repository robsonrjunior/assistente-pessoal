from assistant import send_message


def main():
    while True:
        input_message = input("You: ")
        if input_message.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        response = send_message(input_message)
        print(f"Assistant: {response}")


if __name__ == "__main__":
    main()
