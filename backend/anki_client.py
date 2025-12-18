import os
import httpx
from typing import Any

ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")


class AnkiConnectError(Exception):
    """Error from AnkiConnect API"""
    pass


async def invoke(action: str, **params) -> Any:
    """Make a request to AnkiConnect API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ANKI_CONNECT_URL,
            json={
                "action": action,
                "version": 6,
                "params": params
            },
            timeout=30.0
        )
        result = response.json()

        if result.get("error"):
            raise AnkiConnectError(result["error"])

        return result.get("result")


# Deck operations

async def get_deck_names() -> list[str]:
    """Get all deck names"""
    return await invoke("deckNames")


async def get_deck_names_and_ids() -> dict[str, int]:
    """Get deck names with their IDs"""
    return await invoke("deckNamesAndIds")


async def get_deck_config(deck_name: str) -> dict:
    """Get configuration for a deck including learning steps, intervals, etc."""
    return await invoke("getDeckConfig", deck=deck_name)


# Card operations

async def find_cards(query: str) -> list[int]:
    """Find cards matching a query"""
    return await invoke("findCards", query=query)


async def get_cards_info(card_ids: list[int]) -> list[dict]:
    """Get detailed info for cards"""
    return await invoke("cardsInfo", cards=card_ids)


async def are_due(card_ids: list[int]) -> list[bool]:
    """Check which cards are due"""
    return await invoke("areDue", cards=card_ids)


async def get_intervals(card_ids: list[int]) -> list[int]:
    """Get intervals for cards"""
    return await invoke("getIntervals", cards=card_ids)


async def get_next_intervals(card_ids: list[int]) -> list[list[int]]:
    """
    Get next intervals for all 4 ease buttons.
    Returns array of [again, hard, good, easy] intervals in seconds (negative) or days (positive).
    """
    return await invoke("getIntervals", cards=card_ids, complete=True)


# Review operations

async def answer_cards(answers: list[dict]) -> list[bool]:
    """
    Answer multiple cards.
    Each answer: {"cardId": int, "ease": int}
    Ease: 1=Again, 2=Hard, 3=Good, 4=Easy
    """
    return await invoke("answerCards", answers=answers)


# Sync operations

async def sync() -> None:
    """Trigger sync with AnkiWeb"""
    return await invoke("sync")


# Utility

async def request_permission() -> dict:
    """Request permission to use AnkiConnect"""
    return await invoke("requestPermission")


async def version() -> int:
    """Get AnkiConnect version"""
    return await invoke("version")


# Card queries for vocabulary management

async def get_new_cards(deck_name: str) -> list[int]:
    """Get card IDs for new (unseen) cards in a deck"""
    return await find_cards(f'deck:"{deck_name}" is:new')


async def get_due_cards(deck_name: str) -> list[int]:
    """Get card IDs for cards due for review"""
    return await find_cards(f'deck:"{deck_name}" is:due')


async def get_learned_cards(deck_name: str) -> list[int]:
    """Get card IDs for learned cards (seen before, not due)"""
    return await find_cards(f'deck:"{deck_name}" -is:new -is:due')


async def get_all_cards(deck_name: str) -> list[int]:
    """Get all card IDs in a deck"""
    return await find_cards(f'deck:"{deck_name}"')
