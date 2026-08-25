from speech_to_text import listen


print("NOVA voice test")
print("You have 5 seconds to speak.")

text = listen()

print("\nYou said:")
print(text)