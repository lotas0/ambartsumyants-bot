from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📝 Оформить заказ")],
        [KeyboardButton(text="🧁 Витрина"), KeyboardButton(text="📸 Портфолио")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="🗂 Управление витриной")],
            [KeyboardButton(text="📸 Добавить в портфолио"), KeyboardButton(text="🖼 Управлять портфолио")],
            [KeyboardButton(text="📦 Заявки"), KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def back_to_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ В меню")]],
        resize_keyboard=True,
    )


def products_inline_kb(products: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for p in products:
        text = p["title"]
        if p.get("price"):
            text += f" — {p['price']}"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"product:{p['id']}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else InlineKeyboardMarkup(inline_keyboard=[])


def portfolio_inline_kb(items: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for item in items:
        title = item.get("title") or f"Работа #{item['id']}"
        buttons.append(
            [InlineKeyboardButton(text=title, callback_data=f"portfolio:{item['id']}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else InlineKeyboardMarkup(inline_keyboard=[])


def admin_products_manage_kb(products: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for p in products:
        status = "✅" if p["is_active"] else "❌"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {p['title']}", callback_data=f"adm_prod:{p['id']}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else InlineKeyboardMarkup(inline_keyboard=[])


def admin_portfolio_manage_kb(items: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for item in items:
        title = item.get("title") or f"Работа #{item['id']}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=title, callback_data=f"adm_port:{item['id']}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else InlineKeyboardMarkup(inline_keyboard=[])


def _status_label(status: str) -> str:
    mapping = {
        "new": "Новая",
        "in_progress": "В работе",
        "done": "Завершена",
    }
    return mapping.get(status, status)


def orders_inline_kb(orders: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for o in orders:
        status_text = _status_label(o.get("status", ""))
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Заявка #{o['id']} ({status_text})",
                    callback_data=f"order:{o['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else InlineKeyboardMarkup(inline_keyboard=[])


def order_manage_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершить", callback_data=f"order_done:{order_id}"
                ),
                InlineKeyboardButton(
                    text="🕓 В работе", callback_data=f"order_in_progress:{order_id}"
                ),
            ]
        ]
    )

