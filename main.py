# Interactive chat risk monitor with typo/variation tolerance and detailed breakdown

from difflib import SequenceMatcher

# ---- Scoring settings (change numbers here) ----
STRANGER_THREAT_POINTS = 25
FRIEND_THREAT_POINTS = 15
STRANGER_CONTEXT_POINTS = 20
FRIEND_CONTEXT_POINTS = 10
FRIEND_JOKE_DEDUCTION = -15
STRANGER_JOKE_DEDUCTION = 0
FRIEND_JOKE_BONUS = -10

users_db = {
    "friend_user": {"is_friend": True, "has_jokes": True},
    "stranger_user": {"is_friend": False, "has_jokes": False}
}

suspect_links = {
    "stranger_user": "linked_account_02 (shared media/info before threat)"
}

threat_phrases = [
    "leak your photos",
    "post your pictures",
    "expose you",
    "pay me",
    "send money",
    "send cash",
    "blackmail",
    "ruin your life",
    "kill you",
    "i will kill u",
    "threaten"
]

joke_words = ["haha", "lol", "lmao", "jk", "just kidding", "bro", "😂", "🤣"]


def similar(a, b):
    """Return similarity ratio (0.0 to 1.0) between two strings."""
    return SequenceMatcher(None, a, b).ratio()


def find_threat_matches(text):
    """Find exact or near-match threat phrases in the message."""
    matches = []
    words = text.split()

    # 1. Check phrases against full text or sliding word windows
    for phrase in threat_phrases:
        if phrase in text:
            matches.append((phrase, phrase, 1.0, "exact"))
            continue

        phrase_len = len(phrase.split())
        if phrase_len > 1 and len(words) >= phrase_len:
            best_ratio = 0.0
            best_window = ""
            for i in range(len(words) - phrase_len + 1):
                window = " ".join(words[i:i + phrase_len])
                ratio = similar(phrase, window)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_window = window
            if best_ratio >= 0.78:
                matches.append((best_window, phrase, round(best_ratio, 2), "close phrase"))

    # 2. Check single words for typos/variations
    single_threats = ["kill", "leak", "photos", "pictures", "expose", "pay", "money", "cash", "blackmail", "ruin", "threat"]
    for w in words:
        clean_w = "".join(ch for ch in w if ch.isalnum())
        if not clean_w:
            continue
        for target in single_threats:
            ratio = similar(clean_w, target)
            if clean_w == target:
                matches.append((clean_w, target, 1.0, "exact word"))
            elif ratio >= 0.80 and abs(len(clean_w) - len(target)) <= 2:
                matches.append((clean_w, target, round(ratio, 2), "typo/variation"))

    # Remove duplicate exact/close hits on the exact same fragment
    unique_matches = []
    seen = set()
    for item in matches:
        key = (item[0], item[1])
        if key not in seen:
            seen.add(key)
            unique_matches.append(item)

    # Remove single-word hits already covered by a longer phrase hit
    final_matches = []
    for item in unique_matches:
        found_part = item[0]
        covered = False
        for other in unique_matches:
            other_part = other[0]
            if other_part != found_part and found_part in other_part:
                covered = True
                break
        if not covered:
            final_matches.append(item)
    return final_matches


def find_joke_matches(text):
    """Find joke markers or close variations."""
    found = []
    words = text.split()
    for j in joke_words:
        if j in text:
            found.append((j, 1.0, "exact"))
        else:
            for w in words:
                clean_w = "".join(ch for ch in w if ch.isalnum())
                if clean_w and len(j) >= 3 and similar(clean_w, j) >= 0.80:
                    found.append((clean_w, round(similar(clean_w, j), 2), "similar"))
                    break
    return found


def check_message(sender, msg, current_score, context_applied):
    text = msg.lower()
    profile = users_db.get(sender, {"is_friend": False, "has_jokes": False})
    breakdown = []

    threat_hits = find_threat_matches(text)
    joke_hits = find_joke_matches(text)

    # Threat points: lower for a friend, higher for a stranger
    if profile["is_friend"]:
        pts = FRIEND_THREAT_POINTS
    else:
        pts = STRANGER_THREAT_POINTS

    # Detailed evaluation for each detected threat match
    for found_part, matched_target, ratio, match_type in threat_hits:
        current_score += pts
        breakdown.append(
            f"[+{pts}] Threat match: '{found_part}' -> '{matched_target}' "
            f"(match={match_type}, similarity={ratio})"
        )

    # Context rule: applied only once per chat, at the first threat
    if threat_hits and not context_applied:
        if not profile["is_friend"]:
            extra = STRANGER_CONTEXT_POINTS
            reason = f"sender '{sender}' is not a known friend"
        else:
            extra = FRIEND_CONTEXT_POINTS
            reason = f"sender '{sender}' is a friend, but may be compromised or under pressure"
        current_score += extra
        context_applied = True
        breakdown.append(f"[+{extra}] Context rule: {reason} (applied once)")

    # Joke deduction: friends get a deduction, strangers get none
    if profile["is_friend"]:
        joke_pts = FRIEND_JOKE_DEDUCTION
    else:
        joke_pts = STRANGER_JOKE_DEDUCTION

    if joke_pts != 0:
        for joke_part, ratio, j_type in joke_hits:
            current_score += joke_pts
            breakdown.append(
                f"[{joke_pts}] Joke marker: '{joke_part}' (type={j_type}, similarity={ratio})"
            )

    # Extra deduction if known friend with joke history
    if joke_hits and profile["is_friend"] and profile["has_jokes"]:
        current_score += FRIEND_JOKE_BONUS
        breakdown.append(f"[{FRIEND_JOKE_BONUS}] Context rule: established friend with joke history")

    # Word-by-word overview so every word in the message is accounted for
    word_overview = []
    for raw_word in msg.split():
        lw = raw_word.lower()
        clean_lw = "".join(ch for ch in lw if ch.isalnum() or ch in ["😂", "🤣"])
        tag = "neutral"
        for found_part, _, _, _ in threat_hits:
            if clean_lw and clean_lw in found_part:
                tag = "threat-related"
                break
        for joke_part, _, _ in joke_hits:
            if clean_lw and clean_lw in joke_part:
                tag = "joke-related"
                break
        word_overview.append(f"{raw_word}({tag})")

    if current_score < 0:
        current_score = 0
    if current_score > 100:
        current_score = 100

    return current_score, breakdown, " ".join(word_overview), context_applied


def run_chat():
    name = input("Enter person's name: ").strip()
    if name == "":
        name = "unknown"

    answer = input("Is this person a known friend? (y/n): ").strip().lower()
    is_friend = (answer == "y")

    sender = name
    users_db[sender] = {"is_friend": is_friend, "has_jokes": is_friend}

    score = 0
    context_applied = False
    chat_log = []

    print("\nChat started. Type 'exit' to stop.\n")

    while True:
        msg = input(f"[{sender}]: ").strip()
        if msg.lower() == "exit":
            break
        if msg == "":
            continue

        chat_log.append(msg)
        score, breakdown, word_overview, context_applied = check_message(
            sender, msg, score, context_applied
        )

        if score >= 70:
            level = "HIGH RISK"
        elif score >= 35:
            level = "MEDIUM RISK"
        else:
            level = "LOW RISK"

        print(f"-> Risk Score: {score}/100 | Level: {level}")
        print(f"-> Word-by-word scan: {word_overview}")

        if breakdown:
            print("-> Detailed breakdown:")
            for item in breakdown:
                print(f"   * {item}")
        else:
            print("-> Detailed breakdown: No risk or joke triggers detected (0 change)")

        if score >= 70:
            print("-> ALERT: High threat/extortion score reached.")
            if sender in suspect_links:
                print("-> Network trace:", suspect_links[sender])
        print("-" * 55)

    print("\nSession ended. Total messages:", len(chat_log))
    print("Final Risk Score:", score)


if __name__ == "__main__":
    run_chat()
