# Threat Risk Scoring Tool

A Python prototype that analyzes chat messages and gives a risk score (0-100).

## How it works
- Detects threat keywords and close variations (typo tolerance)
- Gives a higher score if the sender is not a known friend
- Reduces the score for friends when joke markers appear (lol, haha, emojis)
- Counts each threat once and applies the sender-context points once per chat
- Prints a breakdown of every score change

## Limitations
- Keyword-based only, so it can miss threats written in new ways
- Words like "pay" or "money" can cause false alarms
- Does not understand meaning or tone
- Does not remember earlier messages in the chat
- English only

## Notes
Built as a learning project while studying Python, inspired by an
Abu Dhabi Police cybercrime challenge. Developed with AI assistance;
I tested the code and changed the scoring rules myself.

## Run
python main.py
