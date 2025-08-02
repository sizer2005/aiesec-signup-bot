import asyncio
import logging

from src.config import Config
from src.services.communicator import Bot, create_inline_keyboard
from src.services.database import DataBase, Range

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

SHEET_ID = "1nIVD7hAbwVvp1ffI9PolDbtPP_3jjXTI7ixyU24_YGk"
CHAT_ID = "@testbestsest"

city_chats = {
    "Київ": "@Kyiv_RCR_SU_Traker",
    "Львів": "@Lviv_RCR_SU_Traker",
}




async def main():
    config = Config()
    bot = Bot(config)
    database = DataBase(config)

    if not database.tokens.load_tokens(config):
        await database.tokens.login(database.session)

    if database.tokens.token_expired():
        result = await database.tokens.refresh(database.session)
        if not result:
            await database.tokens.login(database.session)

    config.save_tokens(
        database.tokens.access_token,
        database.tokens.refresh_token,
        database.tokens.expires_in,
    )

    names = Range(
        SHEET_ID,
        "LEADS",
        Range.Cell(2, "A"),
        Range.Cell(600, "E"),
    )
    manager = names.copy(Range.Cell(1, "E"))

    range_state = await database.get_range(names)
    updates = await bot.get_updates()

    run = True
    while run:
        await asyncio.sleep(1)
        try:
            updates = await bot.get_updates()
        except Exception as e:
            print(e)
            print("Error while getting updates, retrying")
            updates = []

        for update in updates:
            if "take" in (data := callaback_query(update)):
                callback_id = update["callback_query"]["id"]
                callback_message = update["callback_query"]["message"]
                callback_from = update["callback_query"]["from"]

                chat_id = callback_message["chat"]["id"]
                message_id = callback_message["message_id"]

                await bot.answer_callback(callback_id, "You took the lead")
                await bot.edit_message_text(
                    chat_id,
                    message_id,
                    f"{callback_message['text']}\n\nManage by @{callback_from['username']}",
                    reply_markup=create_inline_keyboard([]),
                )

                manager.start.row = int(data.replace("take", ""))
                await database.update_range(manager, [[callback_from["username"]]])
            elif "/stop" in message(update):
                print(f"Stop by {update}")
                run = False
            elif "/my_leads" in message(update):
                from_user = update["message"]["from"]

                lead_with_manager = names.copy(
                    start=Range.Cell(1, "A"), end=Range.Cell(600, "E")
                )

                lead_with_manager = await database.get_range(lead_with_manager)
                lead_with_manager = "\n".join(
                    [
                        f"{lead[0]}"
                        for lead in lead_with_manager
                        if len(lead) > 1 and lead[1] == from_user["username"]
                    ]
                )
                await bot.send_message(CHAT_ID, lead_with_manager)

        try:
            new_range_state = await database.get_range(names)
        except Exception as e:
            print(e)
            print("Error while getting updates, retrying")
            new_range_state = range_state

        for row_i, row in enumerate(new_range_state[len(range_state):]):
            row_i += len(range_state) + manager.start.row + 1

            city = row[3]
            chat_id = city_chats.get(city, CHAT_ID)

            status = await bot.send_message(
                chat_id,
                f"New lead: {row[0]}\nPhone: {row[1]}\nTelegram: {row[2]}\nLC: {row[3]}",
                reply_markup=create_inline_keyboard([[("Я візьму", f"take{row_i}")]]),
            )

            print(status)
        range_state = new_range_state

        if database.tokens.token_expired():
            result = await database.tokens.refresh(database.session)

    await bot.close()
    await database.close()


def callaback_query(update: dict):
    try:
        return update["callback_query"]["data"]
    except KeyError:
        return ""


def message(update: dict):
    try:
        return update["message"]["text"]
    except KeyError:
        return ""


asyncio.run(main())
