# config.py
from gigachat_config import GigaChatConfig

# ТВОЙ КЛЮЧ (получи в кабинете GigaChat)
GIGACHAT_AUTH_KEY = "MDE5YzkwMTMtZDg1YS03OTE2LTlkNmYtYzI5NzM0NzljN2RhOjEwMTIyZDg5LWIxOTgtNGFiMy1hNTdiLTBmNzdkYWViMzAzOA=="  # замени на реальный!

# СОЗДАЕМ ОБЪЕКТ КОНФИГА (это важно!)
gigachat_config = GigaChatConfig(
    auth_key=GIGACHAT_AUTH_KEY,
    scope="GIGACHAT_API_PERS",
    model="GigaChat",
    temperature=0.5
)