import asyncio
import json
import os
from typing import Dict, List, Optional, Set

from services.pool.redis_pool import RedisPoolManager


class RedisJWTManager:
    """
    Оптимизированный класс для управления JWT-токенами в Redis.
    Использует SCAN вместо KEYS и структурированное хранение.
    """

    def __init__(
        self,
        redis_pool: RedisPoolManager,
        jwt_prefix: str = "jwt:",
        user_tokens_prefix: str = "user_tokens:",
    ):
        self.host = os.environ.get("REDIS_HOST")
        self.port = os.environ.get("REDIS_PORT")
        self.db = os.environ.get("REDIS_DB_NUMBER")
        self.jwt_prefix = jwt_prefix
        self.user_tokens_prefix = user_tokens_prefix
        self.redis_pool = redis_pool

    async def check_connection(self, raise_err: bool = False) -> bool:
        """Проверяет соединение с Redis"""
        try:
            async with asyncio.timeout(2):
                async with self.redis_pool.get_connection() as conn:
                    return await conn.ping()
        except (TimeoutError, asyncio.TimeoutError, Exception) as err:
            if raise_err:
                raise err
            else:
                return False

    # _________________________________________[ОПТИМИЗИРОВАННЫЕ JWT МЕТОДЫ]_________________________________________

    async def add_token(
        self, token: str, email: str, expire_seconds: int = 604800
    ) -> bool:
        """
        Добавляет JWT-токен в Redis с привязкой к email.

        :param token: JWT-токен
        :param email: Email пользователя
        :param expire_seconds: Время жизни токена (по умолчанию 7 дней)
        :return: True если успешно
        """
        async with self.redis_pool.get_connection() as conn:
            # 1. Сохраняем токен с email (для быстрой проверки)
            token_key = f"{self.jwt_prefix}{token}"
            await conn.setex(token_key, expire_seconds, email)

            # 2. Добавляем токен в множество пользователя (для быстрого поиска)
            user_tokens_key = f"{self.user_tokens_prefix}{email}"
            await conn.sadd(user_tokens_key, token)

            # 3. Устанавливаем TTL для user_tokens (немного больше чем у токена)
            await conn.expire(user_tokens_key, expire_seconds + 3600)  # +1 час

            return True

    async def invalidate_token(self, token: str) -> bool:
        """
        Инвалидирует токен и удаляет его из индекса пользователя.

        :param token: JWT-токен
        :return: True если успешно
        """
        async with self.redis_pool.get_connection() as conn:
            # 1. Получаем email из токена
            token_key = f"{self.jwt_prefix}{token}"
            email = await conn.get(token_key)

            if email:
                # 2. Удаляем из индекса пользователя
                user_tokens_key = f"{self.user_tokens_prefix}{email}"
                await conn.srem(user_tokens_key, token)

                # 3. Если у пользователя больше нет токенов, удаляем ключ
                token_count = await conn.scard(user_tokens_key)
                if token_count == 0:
                    await conn.delete(user_tokens_key)

            # 4. Удаляем сам токен
            result = await conn.delete(token_key)
            return result > 0

    async def invalidate_user_tokens(self, email: str, keep_last_n: int = 2) -> int:
        """
        Инвалидирует токены пользователя, оставляя только keep_last_n последних.

        :param email: Email пользователя
        :param keep_last_n: Сколько последних токенов оставить
        :return: Количество удаленных токенов
        """
        async with self.redis_pool.get_connection() as conn:
            user_tokens_key = f"{self.user_tokens_prefix}{email}"

            # 1. Получаем все токены пользователя
            tokens = await conn.smembers(user_tokens_key)
            if not tokens:
                return 0

            # 2. Определяем, какие токены удалить
            tokens_list = list(tokens)
            if keep_last_n:
                tokens_to_keep = (
                    tokens_list[-keep_last_n:]
                    if len(tokens_list) > keep_last_n
                    else tokens_list
                )
                tokens_to_delete = set(tokens_list) - set(tokens_to_keep)
            else:
                tokens_to_delete = set(tokens_list)

            # 3. Удаляем старые токены
            deleted_count = 0
            for token in tokens_to_delete:
                token_key = f"{self.jwt_prefix}{token}"
                await conn.delete(token_key)
                await conn.srem(user_tokens_key, token)
                deleted_count += 1

            # 4. Обновляем множество пользователя
            if tokens_to_keep:
                # Сохраняем только оставшиеся токены
                await conn.delete(user_tokens_key)
                await conn.sadd(user_tokens_key, *tokens_to_keep)
                await conn.expire(user_tokens_key, 604800 + 3600)  # 7 дней + 1 час
            else:
                await conn.delete(user_tokens_key)

            return deleted_count

    async def get_user_tokens(self, email: str) -> Set[str]:
        """
        Получает все токены пользователя по email.

        :param email: Email пользователя
        :return: Множество токенов
        """
        async with self.redis_pool.get_connection() as conn:
            user_tokens_key = f"{self.user_tokens_prefix}{email}"
            return await conn.smembers(user_tokens_key)

    async def get_user_tokens_count(self, email: str) -> int:
        """
        Получает количество токенов пользователя.

        :param email: Email пользователя
        :return: Количество токенов
        """
        async with self.redis_pool.get_connection() as conn:
            user_tokens_key = f"{self.user_tokens_prefix}{email}"
            return await conn.scard(user_tokens_key)

    async def get_token_email(self, token: str) -> Optional[str]:
        """
        Получает email пользователя по токену.

        :param token: JWT-токен
        :return: Email или None
        """
        async with self.redis_pool.get_connection() as conn:
            token_key = f"{self.jwt_prefix}{token}"
            return await conn.get(token_key)

    async def is_token_valid(self, token: str) -> bool:
        """
        Проверяет валидность токена.

        :param token: JWT-токен
        :return: True если токен валиден
        """
        async with self.redis_pool.get_connection() as conn:
            token_key = f"{self.jwt_prefix}{token}"
            return await conn.exists(token_key) == 1

    async def scan_all_tokens(self, batch_size: int = 100) -> List[str]:
        """
        Получает все токены через SCAN (безопасно для продакшена).

        :param batch_size: Размер пачки для SCAN
        :return: Список токенов
        """
        async with self.redis_pool.get_connection() as conn:
            tokens = []
            cursor = 0
            pattern = f"{self.jwt_prefix}*"

            while True:
                cursor, keys = await conn.scan(
                    cursor=cursor, match=pattern, count=batch_size
                )

                for key in keys:
                    token = key[len(self.jwt_prefix) :]
                    tokens.append(token)

                if cursor == 0:
                    break

            return tokens

    async def get_all_tokens_stats(self) -> Dict:
        """
        Получает статистику по токенам.

        :return: Словарь со статистикой
        """
        async with self.redis_pool.get_connection() as conn:
            # Используем SCAN для подсчета токенов
            total_tokens = 0
            cursor = 0
            pattern = f"{self.jwt_prefix}*"

            while True:
                cursor, keys = await conn.scan(cursor=cursor, match=pattern, count=1000)
                total_tokens += len(keys)
                if cursor == 0:
                    break

            # Подсчитываем пользователей
            cursor = 0
            total_users = 0
            user_pattern = f"{self.user_tokens_prefix}*"

            while True:
                cursor, user_keys = await conn.scan(
                    cursor=cursor, match=user_pattern, count=1000
                )
                total_users += len(user_keys)
                if cursor == 0:
                    break

            return {
                "total_tokens": total_tokens,
                "total_users": total_users,
                "avg_tokens_per_user": total_tokens / max(total_users, 1),
            }

    # _________________________________________[CACHE REQUEST МЕТОДЫ]_________________________________________

    async def add_request(
        self, cache_key: str, data: dict, expire_seconds: int = 300
    ) -> bool:
        """
        Добавляет запрос в кэш.

        :param cache_key: Ключ кэша
        :param data: Данные для кэширования
        :param expire_seconds: TTL в секундах
        :return: True если успешно
        """
        async with self.redis_pool.get_connection() as conn:
            try:
                result = await conn.set(
                    cache_key, json.dumps(data, ensure_ascii=False), ex=expire_seconds
                )
                return bool(result)
            except Exception as e:
                print(f"Error caching request: {e}")
                return False

    async def get_request(self, cache_key: str) -> Optional[dict]:
        """
        Получает запрос из кэша.

        :param cache_key: Ключ кэша
        :return: Данные или None
        """
        async with self.redis_pool.get_connection() as conn:
            try:
                cached_data = await conn.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error decoding cached data: {e}")
                # Пытаемся очистить битый кэш
                await conn.delete(cache_key)
            return None

    async def delete_request(self, cache_key: str) -> bool:
        """
        Удаляет запрос из кэша.

        :param cache_key: Ключ кэша
        :return: True если удалено
        """
        async with self.redis_pool.get_connection() as conn:
            result = await conn.delete(cache_key)
            return result > 0

    async def scan_all_requests(self, batch_size: int = 100) -> List[str]:
        """
        Получает все ключи запросов через SCAN.

        :param batch_size: Размер пачки
        :return: Список ключей
        """
        async with self.redis_pool.get_connection() as conn:
            keys = []
            cursor = 0

            # Исключаем JWT ключи и user_tokens ключи
            exclude_patterns = [f"{self.jwt_prefix}*", f"{self.user_tokens_prefix}*"]

            while True:
                cursor, found_keys = await conn.scan(cursor=cursor, count=batch_size)

                for key in found_keys:
                    # Проверяем, что ключ не относится к исключенным паттернам
                    if not key.startswith(self.jwt_prefix) and not key.startswith(
                        self.user_tokens_prefix
                    ):
                        keys.append(key)

                if cursor == 0:
                    break

            return keys

    # _________________________________________[УТИЛИТЫ]_________________________________________

    async def cleanup_expired_tokens(self) -> Dict[str, int]:
        """
        Очищает просроченные токены и обновляет индексы.

        :return: Статистика очистки
        """
        async with self.redis_pool.get_connection() as conn:
            stats = {"tokens_cleaned": 0, "user_indexes_cleaned": 0}

            # 1. Находим все user_tokens ключи
            cursor = 0
            user_pattern = f"{self.user_tokens_prefix}*"

            while True:
                cursor, user_keys = await conn.scan(
                    cursor=cursor, match=user_pattern, count=100
                )

                for user_key in user_keys:
                    # 2. Получаем токены пользователя
                    tokens = await conn.smembers(user_key)
                    valid_tokens = []

                    # 3. Проверяем каждый токен
                    for token in tokens:
                        token_key = f"{self.jwt_prefix}{token}"
                        if await conn.exists(token_key):
                            valid_tokens.append(token)
                        else:
                            stats["tokens_cleaned"] += 1

                    # 4. Обновляем индекс пользователя
                    if valid_tokens:
                        await conn.delete(user_key)
                        await conn.sadd(user_key, *valid_tokens)
                    else:
                        await conn.delete(user_key)
                        stats["user_indexes_cleaned"] += 1

                if cursor == 0:
                    break

            return stats

    async def flush_all_tokens(self) -> bool:
        """
        Очищает ВСЕ токены и индексы (опасно! только для тестов).

        :return: True если успешно
        """
        async with self.redis_pool.get_connection() as conn:
            # Удаляем все токены
            cursor = 0
            while True:
                cursor, keys = await conn.scan(
                    cursor=cursor, match=f"{self.jwt_prefix}*", count=1000
                )
                if keys:
                    await conn.delete(*keys)
                if cursor == 0:
                    break

            # Удаляем все индексы пользователей
            cursor = 0
            while True:
                cursor, user_keys = await conn.scan(
                    cursor=cursor, match=f"{self.user_tokens_prefix}*", count=1000
                )
                if user_keys:
                    await conn.delete(*user_keys)
                if cursor == 0:
                    break

            return True
