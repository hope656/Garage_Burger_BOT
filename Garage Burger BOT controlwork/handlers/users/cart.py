from aiogram import types
from loader import dp, db, bot
from aiogram.dispatcher.storage import FSMContext
from keyboards.default.menu import cart_products_markup, main_menu,cats_markup,phone,location,cancel
from states.main import ShopState
from geopy.geocoders import Nominatim
from utils.misc.product import Product
from data.config import ADMINS
from data.shipping import *


@dp.message_handler(text="КОРЗИНА 🛒", state="*")
async def get_cart_items(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cart_id = db.select_cart(user_id=user_id)[0]
    items = db.get_all_items(cart_id=cart_id)
    if items:
        msg = "«❌ Товар» - удалить товар из корзины\n«🗑 Очистить » - очистить корзину\n\n<i>Товары в корзине:</i>\n\n"
        total_price = 0
        for item in items:
            data = db.get_product_data(id=item[0])
            price = data[-2] * item[1]
            msg += f"<b>{data[1]}</b>\n<code>{data[-2]} x {item[1]} = {price} so'm</code>\n"
            total_price += price
        msg += f"\n\n<i>Всего:</i> <b>{total_price} сум</b>"  
        await message.answer(msg, reply_markup=cart_products_markup(items))
        await ShopState.cart.set()
    else:
        await message.answer("Корзина пустой, пожалуйста заказите 🍟😊")

@dp.message_handler(text="Очистить 🗑", state=ShopState.cart)
async def clear_user_cart(message: types.Message, state: FSMContext):
     user_id = message.from_user.id
     cart_id = db.select_cart(user_id=user_id)[0]
     db.delete_user_cart_items(cart_id=cart_id)
     await message.answer("Успешно удалён😌", reply_markup=main_menu)
     await state.finish()

@dp.message_handler(text="Заказать 🚚", state=ShopState.cart)
async def save_delivery_type(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(phone)
    markup.add(cancel)
    await message.answer("Отправьте или введите Ваш номер телефона:", reply_markup=markup)

@dp.message_handler(content_types=["contact"], state=ShopState.cart)
async def get_user_phone_number(message: types.Message, state: FSMContext):
    await state.update_data({
        "phone": message.contact.phone_number
    })
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(location)
    markup.add(cancel)
    await message.answer("Отправьте Вашу геолокацию:", reply_markup=markup)

@dp.message_handler(content_types=["location"], state=ShopState.cart)
async def get_user_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    data = await state.get_data()
    phone = data.get("phone")
    geoLoc = Nominatim(user_agent="GetLoc")
    locname = geoLoc.reverse(f"{lat}, {lon}")
    address = locname.address
    await state.update_data({"lat": lat, "lon": lon})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="✅Подтверждать✅"))
    markup.add(cancel)
    await message.answer(f"Подтвердите правильность вашей информации для заказа\n\nТелефон номер: {phone}\nАдрес: {address}", reply_markup=markup)


@dp.message_handler(text="❌Отменить❌", state=ShopState.cart)
async def cancel_order(message: types.Message, state: FSMContext):
    await message.answer("Заказ отменен", reply_markup=main_menu)
    await state.finish() 

@dp.message_handler(text="✅Подтверждать✅", state=ShopState.cart)
async def save_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lat = data.get("lat")
    lon = data.get("lon")
    user_id = message.from_user.id
    cart_id = db.select_cart(user_id=user_id)[0]
    items = db.get_all_items(cart_id=cart_id)
    total_price = 0
    msg = ""
    prices = []
    for item in items:
        data = db.get_product_data(id=item[0])
        price = data[-2] * item[1]
        msg += f"{data[1]}({data[-2]}) x {item[1]} = {price} so'm,"
        prices.append(
            types.LabeledPrice(label=data[1], amount=int(price * 100))
        )
        total_price += price    
    db.add_order(user_id=user_id, total_price=total_price, lat=lat, lon=lon)        
    prices.append( 
        LabeledPrice(
            label='Yetkazib berish (7 kun)',
            amount=2000000,# 20 000.00 so'm
        )
    )
    msg += f"Yetkazib berish (7 kun) - 20000 so'm"

    products = Product(
        title="Buyurtmangiz uchun to'lov qiling",
        description=msg,
        start_parameter="create_invoice_order",
        currency="UZS",
        prices=prices,
        need_email=True,
        need_name=True,
        need_phone_number=True,
        need_shipping_address=True, # foydalanuvchi manzilini kiritishi shart
        is_flexible=True
    )

    await bot.send_invoice(chat_id=message.from_user.id, **products.generate_invoice(),payload=f"payload:order_user_id{user_id}")
    
    db.delete_user_cart_items(cart_id=cart_id)
    await state.finish()
@dp.shipping_query_handler()
async def choose_shipping(query: types.ShippingQuery):
    if query.shipping_address.country_code != "UZ":
        await bot.answer_shipping_query(shipping_query_id=query.id,
                                        ok=False,
                                        error_message="Chet elga yetkazib bera olmaymiz")
    elif query.shipping_address.city.lower() == "urganch":
        await bot.answer_shipping_query(shipping_query_id=query.id,
                                        shipping_options=[FAST_SHIPPING, REGULAR_SHIPPING, PICKUP_SHIPPING],
                                        ok=True)
    else:
        await bot.answer_shipping_query(shipping_query_id=query.id,
                                        shipping_options=[REGULAR_SHIPPING],
                                        ok=True)

@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query_id=pre_checkout_query.id,
                                        ok=True)
    await bot.send_message(chat_id=pre_checkout_query.from_user.id,
                           text="Xaridingiz uchun rahmat!",reply_markup=main_menu)
    await bot.send_message(chat_id=ADMINS[0],
                           text=f"Quyidagi mahsulot sotildi: {pre_checkout_query.invoice_payload}\n"
                                f"ID: {pre_checkout_query.id}\n"
                                f"Telegram user: {pre_checkout_query.from_user.first_name}\n"
                                f"Xaridor: {pre_checkout_query.order_info.name}, tel: {pre_checkout_query.order_info.phone_number}")

    
@dp.message_handler(state=ShopState.cart)
async def delete_product(message: types.Message):
    user_id = message.from_user.id
    cart_id = db.select_cart(user_id=user_id)[0]
    product = message.text[2:-2]
    product_id = db.get_product_data(name=product)[0]
    db.delete_product_user_cart(product_id=product_id, cart_id=cart_id)

    items = db.get_all_items(cart_id=cart_id)
    if items:
        msg = "<i>Товары в корзине:</i>\n\n"
        total_price = 0
        for item in items:
            data = db.get_product_data(id=item[0])
            price = data[-2] * item[1]
            msg += f"<b>{data[1]}</b>\n<code>{data[-2]} x {item[1]} = {price} so'm</code>\n"
            total_price += price
        msg += f"\n\n<i>Всего:</i> <b>{total_price} so'm</b>"  
        await message.answer(msg, reply_markup=cart_products_markup(items))
        await ShopState.cart.set()
    else:
         await message.answer("Siz savatchangizni bo'shattingiz 😌, men sizga uni yig'ishda yordam beraman", reply_markup=cats_markup)
         await ShopState.category.set()