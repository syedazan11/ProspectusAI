from src.conversation.session import ConversationSession


session = ConversationSession()

from src.conversation.session import ConversationSession


session = ConversationSession()

for i in range(25):
    session.add_turn(
        "user",
        f"message {i + 1}",
    )

print("Stored:", len(session.recent_turns))
print("First:", session.recent_turns[0]["content"])
print("Last:", session.recent_turns[-1]["content"])

print("\n========== SESSION TEST ==========\n")

print("Total stored turns:", len(session.recent_turns))

for i, turn in enumerate(
    session.recent_turns,
    1,
):
    print(
        f"{i}. {turn['role']}: "
        f"{turn['content']}"
    )

print("\n==================================\n")