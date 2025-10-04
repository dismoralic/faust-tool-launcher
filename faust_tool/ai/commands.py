import re
from typing import Tuple, Union
from telethon import TelegramClient
from .state import is_owner, get_owner_id, set_owner_id

_client: TelegramClient | None = None

def init(client: TelegramClient):
    global _client
    _client = client
    
    async def set_bot_as_owner():
        try:
            me = await client.get_me()
            if me and get_owner_id() is None:
                set_owner_id(me.id)
                print(f"Установлен владелец бота: {me.first_name} (ID: {me.id})")
        except Exception as e:
            print(f"Ошибка при установке владельца: {e}")
    
    client.loop.create_task(set_bot_as_owner())

async def _find_chat_by_name(name: str):
    if not _client:
        return None

    name = name.strip()
    if name.startswith("@"):
        try:
            return await _client.get_entity(name)
        except Exception:
            pass
    if name.isdigit():
        try:
            return await _client.get_entity(int(name))
        except Exception:
            pass

    async for dialog in _client.iter_dialogs():
        if name.lower() in (dialog.name or "").lower():
            return dialog.entity
    return None

async def process_command(
    prompt: str, sender_id: Union[int, str] = None
) -> Tuple[bool, str]:
    if not _client:
        return False, "Клиент ещё не инициализирован."

    if sender_id is not None and not is_owner(sender_id):
        return True, "Отказано в доступе. Только владелец может выполнять команды."

    text = prompt.strip().lower()

    m = re.search(r"(удали(те)?|удалить|стереть)\s+(чат\s)?(с|у)?\s*(.+)", text)
    if m:
        target_name = m.group(5)
        entity = await _find_chat_by_name(target_name)
        if not entity:
            return True, f"Чат с «{target_name}» не найден."
        try:
            await _client.delete_dialog(entity)
            return True, f"Чат с «{target_name}» удалён."
        except Exception as e:
            return True, f"Ошибка при удалении чата: {e}"

    m = re.search(
        r"(стереть|очисти(ть)?|почисти(ть)?|удали(ть)? все сообщения)\s+(чат\s)?(с|у)?\s*(.+)",
        text,
    )
    if m:
        target_name = m.group(8)
        entity = await _find_chat_by_name(target_name)
        if not entity:
            return True, f"Чат с «{target_name}» не найден."
        try:
            async for msg in _client.iter_messages(entity, from_user="me"):
                await _client.delete_messages(entity, msg.id)
            return True, f"Все твои сообщения в чате «{target_name}» удалены."
        except Exception as e:
            return True, f"Ошибка при очистке: {e}"

    return False, ""