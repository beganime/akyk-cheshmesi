def build_direct_chat_key(user_a_uuid: str, user_b_uuid: str) -> str:
    pair = sorted([str(user_a_uuid), str(user_b_uuid)])
    return f"{pair[0]}:{pair[1]}"