from aiogram import types
from states.main import ShopState
from loader import dp, db
from aiogram.dispatcher.storage import FSMContext
from keyboards.default.menu import main_menu, cats_markup, make_products_markup


@dp.message_handler(text="НАЗАД ↩️", state=ShopState.category)
async def go_to_main_menu(message: types.Message):
    await message.answer("Выберите пожалуйста 😊", reply_markup=main_menu)


@dp.message_handler(text="НАЗАД ↩️", state=ShopState.product)
async def go_to_cats_menu(message: types.Message):
    await message.answer("Выберите пожалуйста...", reply_markup=cats_markup)
    await ShopState.category.set()


@dp.message_handler(text="НАЗАД ↩️", state=ShopState.amount)
async def go_to_products_menu(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get("cat_id")
    markup = make_products_markup(cat_id)
    await message.answer("Выберите пожалуйста...", reply_markup=markup)
    await ShopState.product.set()

@dp.message_handler(text="НАЗАД ↩️", state=ShopState.cart)
async def go_to_cats_menu(message: types.Message):
    await message.answer("Выберите пожалуйста 😊...", reply_markup=cats_markup)
    await ShopState.category.set()