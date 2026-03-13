import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from config import load_settings
from database import Database
from keyboards import (
    main_menu_kb,
    admin_menu_kb,
    back_to_menu_kb,
    products_inline_kb,
    portfolio_inline_kb,
    admin_products_manage_kb,
    admin_portfolio_manage_kb,
    orders_inline_kb,
    order_manage_kb,
)


settings = load_settings()
db = Database(settings.db_path)
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Завершена",
}


def human_status(status_code: str) -> str:
    return STATUS_LABELS.get(status_code, status_code)


class OrderForm(StatesGroup):
    weight = State()
    size = State()
    comment = State()
    contact_telegram = State()
    contact_phone = State()


class AddProductForm(StatesGroup):
    title = State()
    description = State()
    price = State()
    photo = State()


class AddPortfolioForm(StatesGroup):
    title = State()
    photo = State()


class BroadcastForm(StatesGroup):
    text = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user:
        db.get_or_create_user(user.id, user.username, user.full_name)

    await message.answer(
        "Здравствуйте! Я бот-кондитер.\n"
        "Помогу оформить заказ на торты, пирожные и другие сладости 😊",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )


@dp.message(F.text == "⬅️ В меню")
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Главное меню:", reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id))
    )


# === Клиент: оформление заказа ===


@dp.message(F.text == "📝 Оформить заказ")
async def start_order(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderForm.weight)
    await message.answer(
        "Укажите, пожалуйста, желаемый вес торта/изделия (например: 1.5 кг):",
        reply_markup=back_to_menu_kb(),
    )


@dp.message(OrderForm.weight)
async def order_weight(message: Message, state: FSMContext) -> None:
    await state.update_data(weight=message.text.strip())
    await state.set_state(OrderForm.size)
    await message.answer("Укажите желаемый размер или форму (например: диаметр 20 см, прямоугольный и т.п.):")


@dp.message(OrderForm.size)
async def order_size(message: Message, state: FSMContext) -> None:
    await state.update_data(size=message.text.strip())
    await state.set_state(OrderForm.comment)
    await message.answer("Опишите пожелания по начинке, оформлению и любым деталям (можно отправить ссылку/описание).\nЕсли особых пожеланий нет — просто напишите «нет».")


@dp.message(OrderForm.comment)
async def order_comment(message: Message, state: FSMContext) -> None:
    await state.update_data(comment=message.text.strip())
    await state.set_state(OrderForm.contact_telegram)
    await message.answer(
        "Оставьте, пожалуйста, ваш Telegram для связи (например: @username).\n"
        "Если не хотите указывать — напишите «нет»."
    )


@dp.message(OrderForm.contact_telegram)
async def order_contact_telegram(message: Message, state: FSMContext) -> None:
    tg = message.text.strip()
    await state.update_data(
        contact_telegram=None if tg.lower() == "нет" else tg
    )
    await state.set_state(OrderForm.contact_phone)
    await message.answer(
        "Укажите, пожалуйста, номер телефона для связи (можно с кодом страны, например: +7...):"
    )


@dp.message(OrderForm.contact_phone)
async def order_contact_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    user = message.from_user
    user_id = None
    if user:
        user_id = db.get_or_create_user(user.id, user.username, user.full_name)

    contact_telegram = data.get("contact_telegram")
    contact_phone = message.text.strip()

    contact_lines = []
    if contact_telegram:
        contact_lines.append(f"Telegram: {contact_telegram}")
    contact_lines.append(f"Телефон: {contact_phone}")
    contact_full = "\n".join(contact_lines)

    order_id = db.add_order(
        user_id=user_id,
        weight=data.get("weight", ""),
        size=data.get("size", ""),
        comment=data.get("comment", ""),
        contact=contact_full,
    )

    await state.clear()

    text = (
        f"Ваша заявка принята! ✅\n\n"
        f"Номер заявки: <b>#{order_id}</b>\n\n"
        f"Вес: {data.get('weight')}\n"
        f"Размер/форма: {data.get('size')}\n"
        f"Пожелания: {data.get('comment')}\n"
        f"Контакты:\n{contact_full}\n\n"
        f"Мы свяжемся с вами в ближайшее время 🙌"
    )
    await message.answer(
        text,
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id)),
    )

    # уведомление админам
    admin_text = (
        f"Новая заявка #{order_id}\n\n"
        f"Вес: {data.get('weight')}\n"
        f"Размер/форма: {data.get('size')}\n"
        f"Пожелания: {data.get('comment')}\n"
        f"Контакты:\n{contact_full}\n"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            continue


# === Клиент: витрина и портфолио ===


@dp.message(F.text == "🧁 Витрина")
async def show_products(message: Message) -> None:
    products = [dict(r) for r in db.list_active_products()]
    if not products:
        await message.answer("Сейчас витрина пуста, но скоро здесь появятся вкусности 😊")
        return

    first = products[0]
    caption_lines = [f"<b>{first['title']}</b>"]
    if first.get("price"):
        caption_lines.append(f"Цена: {first['price']}")
    if first.get("description"):
        caption_lines.append(f"\n{first['description']}")

    if first.get("photo_file_id"):
        await message.answer_photo(
            photo=first["photo_file_id"],
            caption="\n".join(caption_lines),
            reply_markup=products_inline_kb(products),
        )
    else:
        await message.answer(
            "\n".join(caption_lines),
            reply_markup=products_inline_kb(products),
        )


@dp.callback_query(F.data.startswith("product:"))
async def product_detail(call: CallbackQuery) -> None:
    await call.answer()
    product_id = int(call.data.split(":", 1)[1])
    products = [dict(r) for r in db.list_active_products()]
    p = next((x for x in products if x["id"] == product_id), None)
    if not p:
        await call.message.edit_text("Этот товар больше недоступен.")
        return

    caption_lines = [f"<b>{p['title']}</b>"]
    if p.get("price"):
        caption_lines.append(f"Цена: {p['price']}")
    if p.get("description"):
        caption_lines.append(f"\n{p['description']}")

    if call.message.photo and p.get("photo_file_id"):
        try:
            await call.message.edit_media(
                media=InputMediaPhoto(
                    media=p["photo_file_id"],
                    caption="\n".join(caption_lines),
                ),
                reply_markup=products_inline_kb(products),
            )
        except Exception:
            await call.message.edit_text(
                "\n".join(caption_lines),
                reply_markup=products_inline_kb(products),
            )
    else:
        if p.get("photo_file_id"):
            await call.message.answer_photo(
                photo=p["photo_file_id"],
                caption="\n".join(caption_lines),
                reply_markup=products_inline_kb(products),
            )
        else:
            await call.message.edit_text(
                "\n".join(caption_lines),
                reply_markup=products_inline_kb(products),
            )


@dp.message(F.text == "📸 Портфолио")
async def show_portfolio(message: Message) -> None:
    items = [dict(r) for r in db.list_portfolio()]
    if not items:
        await message.answer("Портфолио пока пусто, но скоро здесь будут красивые работы ✨")
        return

    first = items[0]
    caption = first.get("title") or "Работа из портфолио"
    await message.answer_photo(
        photo=first["photo_file_id"],
        caption=caption,
        reply_markup=portfolio_inline_kb(items),
    )


@dp.callback_query(F.data.startswith("portfolio:"))
async def portfolio_detail(call: CallbackQuery) -> None:
    await call.answer()
    item_id = int(call.data.split(":", 1)[1])
    items = [dict(r) for r in db.list_portfolio()]
    item = next((x for x in items if x["id"] == item_id), None)
    if not item:
        await call.message.edit_text("Эта работа больше недоступна.")
        return

    caption = item.get("title") or "Работа из портфолио"
    try:
        await call.message.edit_media(
            media=InputMediaPhoto(
                media=item["photo_file_id"],
                caption=caption,
            ),
            reply_markup=portfolio_inline_kb(items),
        )
    except Exception:
        await call.message.answer_photo(
            photo=item["photo_file_id"],
            caption=caption,
            reply_markup=portfolio_inline_kb(items),
        )


# === Админ-панель ===


@dp.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора.")
        return
    await state.clear()
    await message.answer("Админ-панель:", reply_markup=admin_menu_kb())


# Добавление товара


@dp.message(F.text == "➕ Добавить товар")
async def admin_add_product(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddProductForm.title)
    await message.answer("Введите название товара:", reply_markup=back_to_menu_kb())


@dp.message(AddProductForm.title)
async def add_product_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AddProductForm.description)
    await message.answer("Введите описание товара (или напишите «нет»):")


@dp.message(AddProductForm.description)
async def add_product_description(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    await state.update_data(description=None if desc.lower() == "нет" else desc)
    await state.set_state(AddProductForm.price)
    await message.answer("Укажите цену (например: 1500 ₽/кг) или напишите «нет», если без уточнения:")


@dp.message(AddProductForm.price)
async def add_product_price(message: Message, state: FSMContext) -> None:
    price = message.text.strip()
    await state.update_data(price=None if price.lower() == "нет" else price)
    await state.set_state(AddProductForm.photo)
    await message.answer("Отправьте фото товара одним сообщением (как фото, не как файл):")


@dp.message(AddProductForm.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    product_id = db.add_product(
        title=data["title"],
        description=data.get("description"),
        price=data.get("price"),
        photo_file_id=file_id,
    )
    await state.clear()

    await message.answer(
        f"Товар добавлен на витрину с id #{product_id}.",
        reply_markup=admin_menu_kb(),
    )

    # авторассылка о новом товаре
    users = db.get_all_user_tg_ids()
    text_lines = [f"🧁 Новый товар на витрине!\n\n<b>{data['title']}</b>"]
    if data.get("price"):
        text_lines.append(f"Цена: {data['price']}")
    if data.get("description"):
        text_lines.append(f"\n{data['description']}")
    text = "\n".join(text_lines)

    if users:
        for uid in users:
            try:
                await message.bot.send_photo(
                    chat_id=uid,
                    photo=file_id,
                    caption=text,
                )
            except Exception:
                continue

    # постинг в канал витрины (если задан CHANNEL_ID и бот имеет права писать в канал)
    if settings.channel_id:
        try:
            await message.bot.send_photo(
                chat_id=settings.channel_id,
                photo=file_id,
                caption=text,
            )
        except Exception:
            # если что-то пошло не так (нет прав, неверный id и т.п.) — просто пропускаем
            pass


@dp.message(AddProductForm.photo)
async def add_product_photo_invalid(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте именно фото товара (не документ).")


# Управление витриной


@dp.message(F.text == "🗂 Управление витриной")
async def admin_manage_products(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    products = [dict(r) for r in db.list_all_products()]
    if not products:
        await message.answer("Товаров пока нет.", reply_markup=admin_menu_kb())
        return
    await message.answer(
        "Список товаров. Нажмите, чтобы включить/выключить или удалить.",
        reply_markup=admin_products_manage_kb(products),
    )


@dp.callback_query(F.data.startswith("adm_prod:"))
async def admin_product_action(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    product_id = int(call.data.split(":", 1)[1])
    products = [dict(r) for r in db.list_all_products()]
    p = next((x for x in products if x["id"] == product_id), None)
    if not p:
        await call.message.edit_text("Товар не найден.")
        return

    # переключаем активность
    new_status = not bool(p["is_active"])
    db.set_product_active(product_id, new_status)
    products = [dict(r) for r in db.list_all_products()]
    await call.message.edit_reply_markup(reply_markup=admin_products_manage_kb(products))


# Портфолио управление


@dp.message(F.text == "📸 Добавить в портфолио")
async def admin_add_portfolio(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddPortfolioForm.title)
    await message.answer("Введите название/описание работы (можно пропустить, напишите «нет»):", reply_markup=back_to_menu_kb())


@dp.message(AddPortfolioForm.title)
async def add_portfolio_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    await state.update_data(title=None if title.lower() == "нет" else title)
    await state.set_state(AddPortfolioForm.photo)
    await message.answer("Отправьте фото работы одним сообщением (как фото):")


@dp.message(AddPortfolioForm.photo, F.photo)
async def add_portfolio_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    item_id = db.add_portfolio_item(
        title=data.get("title"),
        photo_file_id=file_id,
    )
    await state.clear()
    await message.answer(
        f"Работа добавлена в портфолио (id #{item_id}).",
        reply_markup=admin_menu_kb(),
    )


@dp.message(AddPortfolioForm.photo)
async def add_portfolio_photo_invalid(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте именно фото (не документ).")


@dp.message(F.text == "🖼 Управлять портфолио")
async def admin_manage_portfolio(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    items = [dict(r) for r in db.list_portfolio()]
    if not items:
        await message.answer("Портфолио пусто.", reply_markup=admin_menu_kb())
        return
    await message.answer(
        "Список работ. Нажмите, чтобы удалить работу.",
        reply_markup=admin_portfolio_manage_kb(items),
    )


@dp.callback_query(F.data.startswith("adm_port:"))
async def admin_portfolio_action(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    item_id = int(call.data.split(":", 1)[1])
    db.delete_portfolio_item(item_id)
    items = [dict(r) for r in db.list_portfolio()]
    if not items:
        await call.message.edit_text("Портфолио пусто.")
        return
    await call.message.edit_reply_markup(reply_markup=admin_portfolio_manage_kb(items))


# Заявки для админа


@dp.message(F.text == "📦 Заявки")
async def admin_orders(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    orders = [dict(r) for r in db.list_orders()]
    if not orders:
        await message.answer("Заявок пока нет.", reply_markup=admin_menu_kb())
        return
    await message.answer(
        "Список заявок:",
        reply_markup=orders_inline_kb(orders),
    )


@dp.callback_query(F.data.startswith("order:"))
async def admin_order_detail(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    order_id = int(call.data.split(":", 1)[1])
    order = db.get_order(order_id)
    if not order:
        await call.message.edit_text("Заявка не найдена.")
        return
    status_text = human_status(order["status"])
    text = (
        f"Заявка #{order['id']}\n"
        f"Статус: {status_text}\n\n"
        f"Вес: {order['weight']}\n"
        f"Размер/форма: {order['size']}\n"
        f"Пожелания: {order['comment']}\n"
        f"Контакты: {order['contact']}\n"
    )
    await call.message.edit_text(text, reply_markup=order_manage_kb(order_id))


@dp.callback_query(F.data.startswith("order_done:"))
async def admin_order_done(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    order_id = int(call.data.split(":", 1)[1])
    db.update_order_status(order_id, "done")
    order = db.get_order(order_id)
    if order:
        status_text = human_status(order["status"])
        text = (
            f"Заявка #{order['id']}\n"
            f"Статус: {status_text}\n\n"
            f"Вес: {order['weight']}\n"
            f"Размер/форма: {order['size']}\n"
            f"Пожелания: {order['comment']}\n"
            f"Контакты: {order['contact']}\n"
        )
        await call.message.edit_text(text, reply_markup=order_manage_kb(order_id))


@dp.callback_query(F.data.startswith("order_in_progress:"))
async def admin_order_in_progress(call: CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    order_id = int(call.data.split(":", 1)[1])
    db.update_order_status(order_id, "in_progress")
    order = db.get_order(order_id)
    if order:
        status_text = human_status(order["status"])
        text = (
            f"Заявка #{order['id']}\n"
            f"Статус: {status_text}\n\n"
            f"Вес: {order['weight']}\n"
            f"Размер/форма: {order['size']}\n"
            f"Пожелания: {order['comment']}\n"
            f"Контакты: {order['contact']}\n"
        )
        await call.message.edit_text(text, reply_markup=order_manage_kb(order_id))


# Рассылка


@dp.message(F.text == "📢 Рассылка")
async def admin_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BroadcastForm.text)
    await message.answer(
        "Отправьте текст рассылки, который получат все пользователи бота:",
        reply_markup=back_to_menu_kb(),
    )


@dp.message(BroadcastForm.text)
async def do_broadcast(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    await state.clear()
    users = db.get_all_user_tg_ids()
    if not users:
        await message.answer("Пока нет пользователей для рассылки.", reply_markup=admin_menu_kb())
        return

    sent = 0
    for uid in users:
        try:
            await message.bot.send_message(uid, text)
            sent += 1
        except Exception:
            continue

    await message.answer(
        f"Рассылка отправлена. Успешно: {sent} из {len(users)}.",
        reply_markup=admin_menu_kb(),
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я помогу оформить заказ на торты и десерты.\n\n"
        "Основные команды:\n"
        "— 📝 Оформить заказ\n"
        "— 🧁 Витрина\n"
        "— 📸 Портфолио\n"
    )


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

