# mindful_eating.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Модуль осознанного питания
Таймер 20 минут — минимальное время для сигнала насыщения
"""

import random
import asyncio
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from utils import has_access, get_user, check_rate_limit, update_user_db

# ВАЖНО: называем роутер по-другому
mindful_router = Router()

print("✅ Импорты в mindful_eating.py выполнены")

# ==================== СОСТОЯНИЯ ====================
class MindfulEating(StatesGroup):
    waiting_start = State()
    water_check = State()
    ritual_check = State()
    smell_check = State()
    first_bite = State()
    photo_check = State()
    second_bite = State()
    colors_check = State()
    hunger_check = State()
    texture_check = State()
    last_bite = State()
    final = State()
    waiting = State()  # Состояние ожидания между вопросами

# ==================== РАНДОМНЫЕ ТЕКСТЫ ====================

WATER_QUESTIONS = [
    "💧 Первым делом: ты выпила стакан воды за 30 минут до еды?",
    "💧 Проверяю: вода была за полчаса до приёма?",
    "💧 Ритуал гидратации: стакан воды уже выпит?"
]

WATER_POSITIVE = [
    "✅ Отлично! Вода запускает пищеварение и готовит желудок.",
    "✅ Супер! Вода сейчас работает как предварительный настрой.",
    "✅ Молодец! Вода активирует рецепторы и улучшит усвоение."
]

WATER_NEGATIVE = [
    "🌱 Ничего страшного. Можешь выпить сейчас маленькими глотками.",
    "🌱 Бывает. Выпей немного сейчас, это лучше чем ничего.",
    "🌱 Окей, просто пей во время еды небольшими глотками."
]

RITUAL_INTROS = [
    "🍴 Теперь проверим настрой:",
    "🧘 Готовимся к осознанному приёму:",
    "✨ Создаём правильную атмосферу:",
    "🌸 Настраиваемся на еду:"
]

RITUAL_ITEMS = {
    "приборы": [
        "красивые приборы на месте?",
        "любимые приборы с тобой?",
        "приборы уже ждут тебя?"
    ],
    "салфетка": [
        "салфетка из бамбука расстелена?",
        "тканевая салфетка готова?",
        "салфетка создаёт уют?"
    ],
    "свеча": [
        "свеча зажжена?",
        "огонь создаёт атмосферу?",
        "свеча уже горит?"
    ],
    "талисман": [
        "возьми в руку Талисман Силы. Почувствуй его.",
        "сожми Талисман, ощути уверенность.",
        "Талисман с тобой? Подержи его в руке."
    ]
}

RITUAL_ADVICE = [
    "Отлично! Теперь закрой глаза на секунду, вдохни и настройся на еду.",
    "Хорошо. Сделай глубокий вдох и почувствуй, как тело готовится к приёму пищи.",
    "Прекрасно. Вдохни аромат еды — это уже запускает пищеварительные ферменты.",
    "Молодец. Такое простое действие переключает мозг в режим пищеварения."
]

SMELL_QUESTIONS = [
    "👃 А теперь понюхай блюдо. Какой аромат чувствуешь?",
    "👃 Вдохни поглубже. Какие ноты улавливаешь?",
    "👃 Аромат — это половина вкуса. Что ощущаешь?"
]

SMELL_OPTIONS = [
    ["🌿 Травяной", "🍖 Мясной", "🍋 Свежий"],
    ["🌶 Пряный", "🧀 Сливочный", "🍅 Насыщенный"],
    ["🌸 Нежный", "🔥 Дымный", "🍯 Сладкий"]
]

SMELL_FACTS = [
    "Нейробиология: запах запускает выработку слюны и ферментов ДО того, как пища попала в рот.",
    "Исследования показывают: осознанное вдыхание аромата усиливает чувство насыщения на 20%.",
    "Обоняние напрямую связано с центром удовольствия в мозге. Наслаждайся!"
]

FIRST_BITE_QUESTIONS = [
    "🍽️ Первый кусочек. Как тебе?",
    "🍽️ Попробуй. Что чувствуешь?",
    "🍽️ Ну как? Вкусно?",
    "🍽️ Первое впечатление?"
]

FIRST_BITE_OPTIONS = [
    ["😋 Очень вкусно", "😐 Нормально", "😕 Так себе"],
    ["🔥 Взрыв вкуса", "👌 Приятно", "🤔 Необычно"],
    ["💫 Идеально", "👍 Хорошо", "🙂 Просто еда"]
]

PHOTO_QUESTIONS = [
    "📸 Сделай фото блюда. Это поможет потом оценить цвет и текстуру.",
    "📸 Щёлкни тарелку на память. Потом сравним ощущения.",
    "📸 Сфотографируй — это поможет закрепить момент осознанности."
]

PHOTO_OPTIONS = [
    "Фото сохранится у тебя в телефоне. Позже можно будет оценить прогресс.",
    "Это для личного архива. Через месяц будет интересно сравнить.",
    "Красивая еда — это тоже часть эстетики питания."
]

TEXTURE_QUESTIONS = [
    "🍲 Какая текстура сейчас во рту?",
    "🍲 Что чувствуешь языком?",
    "🍲 Опиши консистенцию:"
]

TEXTURE_OPTIONS = [
    ["🔸 Хрустящая", "🔸 Мягкая", "🔸 Нежная"],
    ["🔸 Сочная", "🔸 Упругая", "🔸 Воздушная"],
    ["🔸 Твёрдая", "🔸 Кремовая", "🔸 Волокнистая"]
]

HUNGER_QUESTIONS = [
    "🤔 Положи приборы. Прислушайся: ты ещё голодна?",
    "🤔 Сделай паузу. Оцени своё насыщение:",
    "🤔 Остановись на секунду. Что говорит тело?",
    "🤔 Как там желудок? Ещё просит или уже хватит?"
]

HUNGER_OPTIONS = [
    ["🔥 Да, голодна", "⚡ Уже близко", "✅ Сыта"],
    ["💪 Могу ещё", "⏳ Почти наелась", "🌱 Хватит"],
    ["🍽️ Добавки бы", "🤔 Половинку", "🛑 Стоп"]
]

HUNGER_FACTS = [
    "Сигнал насыщения приходит через 15-20 минут. Паузы помогают его услышать.",
    "Исследования: те, кто делает паузы во время еды, съедают на 20% меньше.",
    "В Окинаве говорят: «Хара хачи бу» — ешь, пока не наешься на 80%."
]

LAST_BITE_QUESTIONS = [
    "🍀 Последний кусочек. Съесть или оставить?",
    "🍀 Финальный аккорд. Будешь доедать?",
    "🍀 Завершаем. Этот кусок нужен?"
]

LAST_BITE_OPTIONS = [
    ["😋 Съем с удовольствием", "💫 Оставлю, хватит"],
    ["✨ Доедаю", "🌱 Уже достаточно"]
]

LAST_BITE_FACTS = [
    "Осознанный выбор последнего куска — ключевой навык стройных людей.",
    "Ты только что потренировала навык, который спасёт от тысяч лишних калорий в год.",
    "Молодец! Ты учишься слышать своё тело, а не просто глотать."
]

FINAL_TEXTS = [
    "🎉 Трапеза завершена! Ты провела это время осознанно. Так держать!",
    "✨ Отлично! Теперь ты чувствуешь лёгкость и контроль.",
    "🌟 Прекрасная работа! Твоя осознанность растёт с каждым приёмом пищи."
]

FINAL_TIPS = [
    "💡 Совет: после еды не пей чай 20-30 минут, чтобы не разбавлять желудочный сок.",
    "💡 Маленькая прогулка после еды поможет усвоению.",
    "💡 Похвали себя! Ты только что сделала важный шаг к здоровым привычкам.",
    "💡 Завтрак съешь сам, обед раздели с другом, ужин отдай врагу — старая мудрость.",
    "💡 Инсулиновый цикл: между приёмами должно проходить 3.5-4 часа."
]

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
async def start_mindful_eating(user_id: int, message: types.Message, state: FSMContext):
    """Запуск режима осознанного питания"""
    
    print(f"🍽️ start_mindful_eating вызвана для пользователя {user_id}")
    
    allowed, msg = await check_rate_limit(user_id)
    if not allowed:
        return await message.answer(msg)
    
    user = get_user(user_id)
    if not user:
        print(f"❌ Пользователь {user_id} НЕ найден в БД")
        return await message.answer("Сначала пройди регистрацию: /start")
    
    print(f"✅ В start_mindful_eating пользователь найден: {user.get('power_name', '')}")
    
    # Определяем количество вопросов в зависимости от тарифа
    if has_access(user_id, 'vip'):
        questions_count = 9
        print(f"👑 VIP пользователь: {questions_count} вопросов")
    elif has_access(user_id, 'core'):
        questions_count = 7
        print(f"⭐ CORE пользователь: {questions_count} вопросов")
    else:
        questions_count = 3
        print(f"🆓 FREE пользователь: {questions_count} вопросов")
    
    # 👇 ТАЙМЕР 20 МИНУТ — МИНИМАЛЬНОЕ ВРЕМЯ
    from datetime import datetime, timedelta
    start_time = datetime.now()
    min_end_time = start_time + timedelta(minutes=20)
    
    print(f"⏰ Минимальное время: до {min_end_time.strftime('%H:%M:%S')}")
    
    await state.update_data(
        questions_count=questions_count, 
        current_question=0,
        user_id=user_id,
        start_time=start_time.timestamp(),
        min_end_time=min_end_time.timestamp(),  # минимальное время
        question_sequence=[]
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🍽️ НАЧАТЬ", callback_data="mindful_start")
    kb.button(text="⏸️ ПОЗЖЕ", callback_data="mindful_later")
    
    await message.answer(
        "🍽️ **Режим осознанного питания**\n\n"
        f"Тебя ждёт {questions_count} вопросов.\n"
        "**Минимальное время трапезы: 20 минут**\n"
        "Именно столько нужно мозгу, чтобы получить сигнал насыщения.\n"
        "Если хочешь есть дольше — ешь спокойно, вопросы будут продолжаться.\n\n"
        "Я буду задавать вопросы по ходу трапезы.\n"
        "Ешь медленно, не торопись.\n\n"
        "Начинаем?",
        reply_markup=kb.as_markup()
    )

# ==================== ОБРАБОТЧИКИ ====================

@mindful_router.callback_query(F.data == "mindful_later")
async def mindful_later(callback: types.CallbackQuery, state: FSMContext):
    """Отложить практику"""
    await callback.message.edit_text(
        "⏸️ Хорошо, в другой раз.\n"
        "Просто нажми кнопку «🍽️ РЕЖИМ ЕДЫ», когда будешь готова."
    )
    await state.clear()
    await callback.answer()

@mindful_router.callback_query(F.data == "mindful_start")
async def mindful_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать практику"""
    await callback.message.edit_text(
        "🕐 **Таймер запущен!**\n\n"
        "Минимальное время трапезы: 20 минут.\n"
        "Я буду задавать вопросы по ходу еды.\n"
        "Ешь спокойно, никуда не торопись.\n\n"
        "Первый вопрос через 30 секунд..."
    )
    await callback.answer()
    
    # Сохраняем время старта
    data = await state.get_data()
    await state.update_data(start_time=datetime.now().timestamp())
    
    # Запускаем первую задачу с задержкой 30 секунд
    asyncio.create_task(schedule_next_question(callback.message, state, delay=30))

async def schedule_next_question(message: types.Message, state: FSMContext, delay=30):
    """Запланировать следующий вопрос с задержкой"""
    await asyncio.sleep(delay)
    
    # Проверяем данные
    data = await state.get_data()
    current = data.get('current_question', 0)
    questions_count = data.get('questions_count', 0)
    
    # Если вопросы еще не закончились, задаем следующий
    if current < questions_count:
        await ask_water(message, state)
    else:
        # Вопросы закончились, завершаем
        await finish_eating(message, state)

async def finish_eating_timeout(message: types.Message, state: FSMContext):
    """Завершение после минимального времени (20 минут)"""
    data = await state.get_data()
    user_id = data.get('user_id', message.from_user.id)
    current = data.get('current_question', 0)
    questions_count = data.get('questions_count', 0)
    
    # Если вопросы еще не закончились, продолжаем без ограничения времени
    if current < questions_count:
        print("⏰ 20 минут прошло, но вопросы еще есть — продолжаем без таймера")
        # Просто продолжаем задавать следующие вопросы
        await ask_next_question_after_timeout(message, state, current)
        return
    
    # Если вопросы закончились — завершаем
    await state.clear()
    await message.answer(
        "✅ **20 минут прошло!**\n\n"
        "Ты провела за едой достаточно времени, чтобы мозг получил сигнал насыщения.\n"
        "Если хочешь продолжать есть — ешь спокойно дальше.\n\n"
        "Хорошего аппетита! 🌿"
    )

async def ask_next_question_after_timeout(message: types.Message, state: FSMContext, current: int):
    """Задать следующий вопрос после таймаута"""
    # Определяем следующий вопрос
    # Упрощенно — просто продолжаем последовательность
    await ask_water(message, state)

@mindful_router.callback_query(F.data.startswith("next_"))
async def next_question_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переход к следующему вопросу"""
    await callback.answer()
    
    # Получаем следующий шаг из callback_data
    next_step = callback.data.replace("next_", "")
    
    # Словарь соответствия шагов и функций
    step_functions = {
        "water": ask_water,
        "ritual": ask_ritual,
        "smell": ask_smell,
        "first": ask_first_bite,
        "photo": ask_photo,
        "second": ask_second_bite,
        "colors": ask_colors,
        "hunger": ask_hunger,
        "texture": ask_texture,
        "last": ask_last_bite,
        "final": finish_eating
    }
    
    if next_step in step_functions:
        # Запускаем следующий вопрос с задержкой 60-120 секунд
        delay = random.randint(60, 120)
        await callback.message.answer(f"⏳ Следующий вопрос через {delay//60}:{delay%60:02d}...")
        asyncio.create_task(schedule_question(callback.message, state, step_functions[next_step], delay))

async def schedule_question(message: types.Message, state: FSMContext, question_func, delay):
    """Запланировать конкретный вопрос"""
    await asyncio.sleep(delay)
    
    # Проверяем, не вышли ли вопросы
    data = await state.get_data()
    current = data.get('current_question', 0)
    questions_count = data.get('questions_count', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await question_func(message, state)

# ==================== ВОПРОСЫ ====================

async def ask_water(message: types.Message, state: FSMContext):
    """Вопрос про воду"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="water")
    
    question = random.choice(WATER_QUESTIONS)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ ДА", callback_data="water_yes")
    kb.button(text="❌ НЕТ", callback_data="water_no")
    
    await message.answer(question, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data == "water_yes")
async def water_yes(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(random.choice(WATER_POSITIVE))
    await callback.answer()
    
    # Планируем следующий вопрос через 90 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "ritual", 90))

@mindful_router.callback_query(F.data == "water_no")
async def water_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(random.choice(WATER_NEGATIVE))
    await callback.answer()
    
    # Планируем следующий вопрос через 60 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "ritual", 60))

async def schedule_next_question_by_state(message: types.Message, state: FSMContext, next_state, delay):
    """Запланировать следующий вопрос по состоянию"""
    await asyncio.sleep(delay)
    
    # Проверяем данные
    data = await state.get_data()
    current = data.get('current_question', 0)
    questions_count = data.get('questions_count', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    # Вызываем соответствующий вопрос
    if next_state == "ritual":
        await ask_ritual(message, state)
    elif next_state == "smell":
        await ask_smell(message, state)
    elif next_state == "first":
        await ask_first_bite(message, state)
    elif next_state == "photo":
        await ask_photo(message, state)
    elif next_state == "second":
        await ask_second_bite(message, state)
    elif next_state == "colors":
        await ask_colors(message, state)
    elif next_state == "hunger":
        await ask_hunger(message, state)
    elif next_state == "texture":
        await ask_texture(message, state)
    elif next_state == "last":
        await ask_last_bite(message, state)

async def ask_ritual(message: types.Message, state: FSMContext):
    """Проверка ритуальных предметов"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="ritual")
    
    # Случайный порядок предметов
    items_order = ["приборы", "салфетка", "свеча", "талисман"]
    random.shuffle(items_order)
    
    text = random.choice(RITUAL_INTROS) + "\n\n"
    for item in items_order:
        question = random.choice(RITUAL_ITEMS[item])
        text += f"• {question}\n"
    
    text += "\n" + random.choice(RITUAL_ADVICE)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ ДА, ВСЁ ГОТОВО", callback_data="ritual_done")
    
    await message.answer(text, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data == "ritual_done")
async def ritual_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✨ Отлично! Ты создала правильную атмосферу.")
    await callback.answer()
    
    # Следующий вопрос через 60 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "smell", 60))

async def ask_smell(message: types.Message, state: FSMContext):
    """Вопрос про аромат"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="smell")
    
    question = random.choice(SMELL_QUESTIONS)
    options = random.choice(SMELL_OPTIONS)
    fact = random.choice(SMELL_FACTS)
    
    kb = InlineKeyboardBuilder()
    for opt in options:
        callback_data = f"smell_{opt.split()[-1][:10]}"
        kb.button(text=opt, callback_data=callback_data)
    
    await message.answer(
        question + "\n\n" + fact,
        reply_markup=kb.as_markup()
    )

@mindful_router.callback_query(F.data.startswith("smell_"))
async def smell_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👃 Запомни этот аромат. Он часть твоего опыта.")
    await callback.answer()
    
    # Следующий вопрос через 90 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "first", 90))

async def ask_first_bite(message: types.Message, state: FSMContext):
    """Первый кусочек"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="first_bite")
    
    question = random.choice(FIRST_BITE_QUESTIONS)
    options = random.choice(FIRST_BITE_OPTIONS)
    
    kb = InlineKeyboardBuilder()
    for opt in options:
        callback_data = f"first_{opt.split()[0][:2]}"
        kb.button(text=opt, callback_data=callback_data)
    
    await message.answer(question, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data.startswith("first_"))
async def first_bite_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("😋 Отлично! Продолжай жевать медленно.")
    await callback.answer()
    
    # Следующий вопрос через 120 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "photo", 120))

async def ask_photo(message: types.Message, state: FSMContext):
    """Предложение сделать фото"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="photo")
    
    text = random.choice(PHOTO_QUESTIONS) + "\n\n" + random.choice(PHOTO_OPTIONS)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📸 СДЕЛАТЬ ФОТО", callback_data="photo_take")
    kb.button(text="⏩ ПРОПУСТИТЬ", callback_data="photo_skip")
    
    await message.answer(text, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data == "photo_take")
async def photo_take(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📸 Фото сохранится у тебя в телефоне. Продолжай есть.")
    await callback.answer()
    
    # Следующий вопрос через 90 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "second", 90))

@mindful_router.callback_query(F.data == "photo_skip")
async def photo_skip(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⏩ Окей, просто наслаждайся едой.")
    await callback.answer()
    
    # Следующий вопрос через 60 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "second", 60))

async def ask_second_bite(message: types.Message, state: FSMContext):
    """Второй кусочек и пауза"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="second_bite")
    
    text = "🍽️ Ещё кусочек... А теперь положи приборы на 10 секунд. Просто посиди с закрытыми глазами."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⏸️ ПРИБОРЫ ПОЛОЖИЛА", callback_data="utensils_down")
    
    await message.answer(text, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data == "utensils_down")
async def utensils_down(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🧘 Хорошо. Чувствуешь, как уходит спешка?")
    await callback.answer()
    
    # Следующий вопрос через 90 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "colors", 90))

async def ask_colors(message: types.Message, state: FSMContext):
    """Сколько цветов на тарелке"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="colors")
    
    text = "🎨 Сколько цветов на твоей тарелке? (чем больше цветов, тем больше нутриентов)"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="1-2 цвета", callback_data="colors_1")
    kb.button(text="3 цвета", callback_data="colors_2")
    kb.button(text="4+ цвета", callback_data="colors_3")
    
    await message.answer(text, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data.startswith("colors_"))
async def colors_chosen(callback: types.CallbackQuery, state: FSMContext):
    colors_count = callback.data.replace("colors_", "")
    emoji = "🌈" if colors_count == "3" else "🎨"
    await callback.message.edit_text(f"{emoji} Красиво! Разнообразие цветов = разнообразие нутриентов.")
    await callback.answer()
    
    # Следующий вопрос через 120 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "hunger", 120))

async def ask_hunger(message: types.Message, state: FSMContext):
    """Проверка голода"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="hunger")
    
    question = random.choice(HUNGER_QUESTIONS)
    options = random.choice(HUNGER_OPTIONS)
    fact = random.choice(HUNGER_FACTS)
    
    kb = InlineKeyboardBuilder()
    for opt in options:
        callback_data = f"hunger_{opt.split()[0][:2]}"
        kb.button(text=opt, callback_data=callback_data)
    
    await message.answer(
        question + "\n\n" + fact,
        reply_markup=kb.as_markup()
    )

@mindful_router.callback_query(F.data.startswith("hunger_"))
async def hunger_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🤔 Хорошо, что спросила себя об этом.")
    await callback.answer()
    
    # Следующий вопрос через 90 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "texture", 90))

async def ask_texture(message: types.Message, state: FSMContext):
    """Текстура еды"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="texture")
    
    question = random.choice(TEXTURE_QUESTIONS)
    options = random.choice(TEXTURE_OPTIONS)
    
    kb = InlineKeyboardBuilder()
    for opt in options:
        callback_data = f"texture_{opt.split()[1][:5]}" if len(opt.split()) > 1 else f"texture_{opt[:5]}"
        kb.button(text=opt, callback_data=callback_data)
    
    await message.answer(question, reply_markup=kb.as_markup())

@mindful_router.callback_query(F.data.startswith("texture_"))
async def texture_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👄 Текстура — важная часть удовольствия от еды.")
    await callback.answer()
    
    # Следующий вопрос через 120 секунд
    asyncio.create_task(schedule_next_question_by_state(callback.message, state, "last", 120))

async def ask_last_bite(message: types.Message, state: FSMContext):
    """Последний кусочек"""
    data = await state.get_data()
    questions_count = data.get('questions_count', 3)
    current = data.get('current_question', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
        return
    
    await state.update_data(current_question=current + 1, current_state="last_bite")
    
    question = random.choice(LAST_BITE_QUESTIONS)
    options = random.choice(LAST_BITE_OPTIONS)
    fact = random.choice(LAST_BITE_FACTS)
    
    kb = InlineKeyboardBuilder()
    for opt in options:
        callback_data = f"last_{opt.split()[0][:2]}"
        kb.button(text=opt, callback_data=callback_data)
    
    await message.answer(
        question + "\n\n" + fact,
        reply_markup=kb.as_markup()
    )

@mindful_router.callback_query(F.data.startswith("last_"))
async def last_bite_chosen(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🍀 Отлично! Ты справилась.")
    await callback.answer()
    
    # Завершаем через 30 секунд
    asyncio.create_task(schedule_finish(callback.message, state, 30))

async def schedule_finish(message: types.Message, state: FSMContext, delay):
    """Запланировать завершение"""
    await asyncio.sleep(delay)
    
    # Проверяем, все ли вопросы заданы
    data = await state.get_data()
    current = data.get('current_question', 0)
    questions_count = data.get('questions_count', 0)
    
    if current >= questions_count:
        await finish_eating(message, state)
    else:
        # Если вопросы еще есть, просто продолжаем
        pass

async def finish_eating(message: types.Message, state: FSMContext):
    """Завершение трапезы"""
    data = await state.get_data()
    user_id = data.get('user_id', message.from_user.id)
    
    # Начисляем баллы за осознанное питание
    try:
        from bot import award_points
        await award_points(user_id, "mindful_eating", message)
    except Exception as e:
        print(f"Ошибка при начислении баллов: {e}")
    
    await state.clear()
    
    text = random.choice(FINAL_TEXTS) + "\n\n" + random.choice(FINAL_TIPS)
    
    # Кнопка для следующего приёма
    kb = InlineKeyboardBuilder()
    kb.button(text="⏰ СЛЕДУЮЩИЙ ПРИЁМ", callback_data="next_meal")
    kb.button(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
    
    await message.answer(text, reply_markup=kb.as_markup())


@mindful_router.callback_query(F.data == "next_meal")
async def next_meal_callback(callback: types.CallbackQuery):
    """Напоминание о следующем приёме"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔸 Через 3.5 часа", callback_data="remind_3.5")
    kb.button(text="🔸 Через 4 часа", callback_data="remind_4")
    kb.button(text="🔸 Через 5 часов", callback_data="remind_5")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "⏰ **Когда планируешь следующий приём пищи?**\n\n"
        "Инсулиновый цикл составляет 3.5-4 часа.\n"
        "Выбери удобное время:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@mindful_router.callback_query(F.data.startswith("remind_"))
async def set_reminder_callback(callback: types.CallbackQuery):
    """Установить напоминание"""
    hours = callback.data.replace("remind_", "")
    await callback.message.edit_text(
        f"✅ Напомню через {hours} часа. Хорошего дня!\n"
        f"Главное меню: /menu"
    )
    await callback.answer()


@mindful_router.callback_query(F.data == "main_menu")
async def back_to_main_menu_callback(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    from menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message)
    await callback.answer()


# Добавим обработчик для случая, если пользователь случайно отправил сообщение
@mindful_router.message(F.text)
async def unexpected_message(message: types.Message, state: FSMContext):
    """Обработка неожиданных сообщений во время практики"""
    current_state = await state.get_state()
    if current_state and current_state.startswith("MindfulEating"):
        await message.answer(
            "🍽️ Сейчас идёт практика осознанного питания.\n"
            "Пожалуйста, отвечай на вопросы с помощью кнопок ниже."
        )

print("✅ Все хэндлеры в mindful_eating.py зарегистрированы")
print("🔥🔥🔥 MINDFUL_EATING.PY ЗАГРУЗКА ЗАВЕРШЕНА 🔥🔥🔥")

# ==================== ЭКСПОРТ ====================
__all__ = ['mindful_router', 'start_mindful_eating']