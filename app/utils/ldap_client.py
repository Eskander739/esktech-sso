"""Клиент для LDAP/Active Directory."""
import asyncio
import traceback
from typing import Any

import ldap
from config import settings
from log import logger


async def authenticate_ldap(username: str, password: str) -> dict[str, Any] | None:
    """
    Аутентификация через LDAP.
    Возвращает словарь с информацией о пользователе или None.

    Args:
        username: Имя пользователя для аутентификации
        password: Пароль пользователя

    Returns:
        dict с информацией о пользователе или None при ошибке
    """
    logger.info(f"Начало LDAP аутентификации для пользователя: {username}")
    settings.LDAP_URI = "ldap://localhost:389"
    settings.LDAP_BASE_DN = "uid=ldap_user,ou=users, dc=example,dc=org"
    settings.LDAP_USER_ATTR = "uid"

    # Проверка конфигурации LDAP
    if not settings.LDAP_URI:
        logger.debug("LDAP не настроен (LDAP_URI отсутствует), пропускаем аутентификацию")
        return None

    if not settings.LDAP_BASE_DN:
        logger.warning("LDAP_BASE_DN не настроен, аутентификация невозможна")
        return None

    # Логируем конфигурацию (без sensitive данных)
    logger.debug(f"LDAP URI: {settings.LDAP_URI}")
    logger.debug(f"LDAP Base DN: {settings.LDAP_BASE_DN}")
    logger.debug(f"LDAP User Attribute: {settings.LDAP_USER_ATTR}")

    # Проверка учетных данных
    if not username or not password:
        logger.warning(f"Пустые учетные данные: username={bool(username)}, password={bool(password)}")
        return None

    loop = asyncio.get_running_loop()

    try:
        result = await loop.run_in_executor(None, _sync_ldap_auth, username, password)

        if result:
            logger.info(f"Успешная LDAP аутентификация для пользователя: {username}")
            logger.debug(f"Получены данные пользователя: email={result.get('email')}, full_name={result.get('full_name')}")
        else:
            logger.warning(f"Неудачная LDAP аутентификация для пользователя: {username}")

        return result

    except asyncio.CancelledError:
        logger.error(f"Асинхронная операция LDAP была отменена для пользователя: {username}")
        raise
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при асинхронной LDAP аутентификации для {username}: {e}")
        return None


def _decode_ldap_error(e: Exception) -> tuple[int, str, dict]:
    """
    Расшифровка LDAP ошибки с получением деталей.

    Returns:
        tuple: (код_ошибки, сообщение_об_ошибке, детали_ошибки)
    """
    error_code = 0
    error_message = str(e)
    error_details = {}

    try:
        # Получаем полную информацию об ошибке
        if hasattr(e, 'args') and e.args:
            args = e.args[0] if e.args else None

            # Различные форматы ошибок LDAP
            if isinstance(args, dict):
                # Формат: {'desc': '...', 'info': '...', 'errno': ...}
                error_code = args.get('errno', args.get('code', 0))
                error_message = args.get('desc', 'Unknown')
                info = args.get('info', '')
                if info:
                    error_message = f"{error_message}: {info}"
                error_details = args

            elif isinstance(args, tuple) and len(args) >= 2:
                # Формат: (code, message)
                error_code = args[0]
                error_message = str(args[1])
                error_details = {'code': error_code, 'message': error_message}

            elif isinstance(args, str):
                error_message = args
                error_details = {'description': args}

    except Exception as parse_error:
        logger.debug(f"Ошибка при парсинге LDAP ошибки: {parse_error}")

    return error_code, error_message, error_details


def _sync_ldap_auth(username: str, password: str) -> dict[str, Any] | None:
    """
    Синхронная реализация LDAP-аутентификации.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        dict с данными пользователя или None
    """
    conn = None
    logger.debug(f"=== НАЧАЛО СИНХРОННОЙ LDAP АУТЕНТИФИКАЦИИ для: {username} ===")

    try:
        # Шаг 1: Инициализация соединения
        logger.debug(f"Шаг 1/5: Инициализация LDAP соединения с {settings.LDAP_URI}")
        conn = ldap.initialize(settings.LDAP_URI)

        # Шаг 2: Настройка опций соединения
        logger.debug("Шаг 2/5: Настройка опций соединения")
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5.0)
        conn.set_option(ldap.OPT_TIMEOUT, 5.0)
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        # Дополнительные опции для совместимости
        conn.set_option(ldap.OPT_RESTART, 1)  # Перезапуск прерванных операций

        # Настройка TLS если используется ldaps
        if settings.LDAP_URI.startswith('ldaps://'):
            logger.debug("Настройка TLS для LDAPS соединения")
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # Для тестов
            conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)

        logger.debug("Опции LDAP успешно настроены")

        # Шаг 3: Формирование DN для привязки
        logger.debug("Шаг 3/5: Формирование DN для привязки")

        # Поддержка разных форматов username
        if '@' in username and '.' in username and '\\' not in username:
            # Возможно это UPN (user@domain.com) для AD
            bind_dn = username
            logger.debug(f"Используем UPN формат: {bind_dn}")
        elif '\\' in username:
            # Формат DOMAIN\\username для AD
            bind_dn = username
            logger.debug(f"Используем DOMAIN\\username формат: {bind_dn}")
        else:
            # Обычный DN формат для OpenLDAP
            bind_dn = f"{settings.LDAP_USER_ATTR}={username},{settings.LDAP_BASE_DN}"
            logger.debug(f"Используем DN формат: {bind_dn}")

        # Шаг 4: Аутентификация
        logger.info(f"Шаг 4/5: Попытка привязки к LDAP серверу")
        logger.debug(f"Bind DN: {bind_dn}")

        try:
            conn.simple_bind_s(bind_dn, password)
            logger.info("✓ LDAP привязка успешна!")
        except ldap.INVALID_CREDENTIALS as e:
            code, msg, details = _decode_ldap_error(e)
            logger.warning(f"✗ Неверные учетные данные (код {code}): {msg}")
            logger.debug(f"Детали ошибки: {details}")
            return None
        except ldap.SERVER_DOWN as e:
            code, msg, details = _decode_ldap_error(e)
            logger.error(f"✗ LDAP сервер недоступен (код {code}): {msg}")
            logger.error(f"  Проверьте доступность: {settings.LDAP_URI}")
            logger.debug(f"Детали ошибки: {details}")
            return None
        except ldap.TIMEOUT as e:
            code, msg, details = _decode_ldap_error(e)
            logger.error(f"✗ Таймаут соединения (код {code}): {msg}")
            logger.debug(f"Детали ошибки: {details}")
            return None

        # Шаг 5: Поиск информации о пользователе
        logger.debug("Шаг 5/5: Поиск информации о пользователе")

        # Пробуем разные фильтры для совместимости с различными LDAP серверами
        search_filters = [
            f"(&(objectClass=user)({settings.LDAP_USER_ATTR}={username}))",  # AD формат
            f"(&(objectClass=person)({settings.LDAP_USER_ATTR}={username}))",  # Общий формат
            f"(&(objectClass=inetOrgPerson)({settings.LDAP_USER_ATTR}={username}))",  # OpenLDAP формат
            f"({settings.LDAP_USER_ATTR}={username})",  # Простой фильтр
        ]

        attributes = [
            "mail", "email", "displayName", "cn", "sn", "givenName",
            "sAMAccountName", "userPrincipalName", "uid", "name"
        ]

        user_data = None

        for search_filter in search_filters:
            logger.debug(f"Пробуем фильтр поиска: {search_filter}")

            try:
                result = conn.search_s(
                    settings.LDAP_BASE_DN,
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    attributes
                )

                logger.debug(f"Результат поиска: найдено {len(result)} записей")

                if result:
                    dn, attrs = result[0]
                    logger.debug(f"Найден DN: {dn}")
                    logger.debug(f"Доступные атрибуты: {list(attrs.keys())}")

                    # Извлекаем данные пользователя
                    user_data = _extract_user_data(username, attrs)

                    if user_data:
                        logger.info(f"✓ Данные пользователя успешно получены через фильтр: {search_filter}")
                        break
                    else:
                        logger.warning(f"Не удалось извлечь данные из атрибутов: {attrs}")

            except ldap.NO_SUCH_OBJECT:
                logger.debug(f"Base DN не найден для фильтра {search_filter}")
                continue
            except ldap.FILTER_ERROR as e:
                code, msg, details = _decode_ldap_error(e)
                logger.debug(f"Ошибка фильтра {search_filter}: {msg}")
                continue
            except ldap.LDAPError as e:
                code, msg, details = _decode_ldap_error(e)
                logger.debug(f"LDAP ошибка при поиске: {msg}")
                continue

        # Если пользователь не найден, но аутентификация прошла успешно
        if not user_data:
            logger.warning(f"Пользователь {username} не найден в LDAP каталоге, но аутентификация успешна")
            user_data = {
                "username": username,
                "email": f"{username}@ldap.local",
                "full_name": username,
            }
            logger.debug("Возвращаем fallback данные")

        return user_data

    except ldap.LDAPError as e:
        code, msg, details = _decode_ldap_error(e)
        logger.error(f"✗ Общая LDAP ошибка (код {code}): {msg}")
        logger.error(f"  Тип ошибки: {type(e).__name__}")
        logger.debug(f"  Детали ошибки: {details}")
        logger.debug(f"  Полное представление: {repr(e)}")

        # Диагностика возможных проблем
        logger.error("  Возможные причины:")
        logger.error("    1. Неверный формат DN или Base DN")
        logger.error("    2. Проблемы с TLS/SSL сертификатом")
        logger.error("    3. Неподдерживаемая версия LDAP протокола")
        logger.error("    4. Проблемы с кодировкой символов")
        logger.error(f"    5. Проверьте настройки: URI={settings.LDAP_URI}, Base DN={settings.LDAP_BASE_DN}")

        return None

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"✗ Сетевая ошибка: {type(e).__name__} - {e}")
        return None

    except UnicodeDecodeError as e:
        logger.error(f"✗ Ошибка декодирования Unicode: {e}")
        logger.error(f"  Проблемное поле: {e.reason} на позиции {e.start}")
        logger.debug(f"  Объект с ошибкой: {e.object if hasattr(e, 'object') else 'N/A'}")
        return None

    except Exception as e:
        logger.exception(f"✗ Неожиданная ошибка: {type(e).__name__} - {e}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        return None

    finally:
        if conn:
            try:
                logger.debug("Закрытие LDAP соединения...")
                conn.unbind()
                logger.debug("✓ LDAP соединение успешно закрыто")
            except ldap.LDAPError as e:
                logger.warning(f"Ошибка при закрытии LDAP соединения: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при закрытии соединения: {e}")

        logger.debug(f"=== ЗАВЕРШЕНИЕ LDAP АУТЕНТИФИКАЦИИ ===")


def _extract_user_data(username: str, attrs: dict) -> dict[str, Any] | None:
    """
    Извлекает данные пользователя из атрибутов LDAP.

    Args:
        username: Имя пользователя
        attrs: Словарь с атрибутами LDAP

    Returns:
        dict с данными пользователя или None
    """
    try:
        # Функция для безопасного декодирования
        def decode_value(value):
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value) if value else ""

        # Извлечение email (пробуем разные атрибуты)
        email = ""
        for email_attr in ["mail", "email", "userPrincipalName"]:
            if email_attr in attrs and attrs[email_attr]:
                email = decode_value(attrs[email_attr][0])
                if email:
                    logger.debug(f"Найден email из {email_attr}: {email}")
                    break

        if not email:
            logger.debug("Email не найден, будет использован email по умолчанию")
            email = f"{username}@ldap.local"

        # Извлечение полного имени
        full_name = ""

        # Пробуем displayName
        if "displayName" in attrs and attrs["displayName"]:
            full_name = decode_value(attrs["displayName"][0])
            logger.debug(f"Найден displayName: {full_name}")

        # Пробуем собрать из givenName и sn
        if not full_name:
            first_name = ""
            last_name = ""

            if "givenName" in attrs and attrs["givenName"]:
                first_name = decode_value(attrs["givenName"][0])
                logger.debug(f"Найден givenName: {first_name}")

            if "sn" in attrs and attrs["sn"]:
                last_name = decode_value(attrs["sn"][0])
                logger.debug(f"Найден sn: {last_name}")

            if first_name or last_name:
                full_name = f"{first_name} {last_name}".strip()
                logger.debug(f"Собрано имя из first/last: {full_name}")

        # Пробуем cn (common name)
        if not full_name and "cn" in attrs and attrs["cn"]:
            full_name = decode_value(attrs["cn"][0])
            logger.debug(f"Найден cn: {full_name}")

        # Пробуем name
        if not full_name and "name" in attrs and attrs["name"]:
            full_name = decode_value(attrs["name"][0])
            logger.debug(f"Найден name: {full_name}")

        if not full_name:
            logger.debug("Полное имя не найдено, используем username")
            full_name = username

        # Дополнительная информация для отладки
        if "sAMAccountName" in attrs:
            logger.debug(f"sAMAccountName: {decode_value(attrs['sAMAccountName'][0])}")
        if "uid" in attrs:
            logger.debug(f"uid: {decode_value(attrs['uid'][0])}")

        return {
            "username": username,
            "email": email,
            "full_name": full_name,
        }

    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        logger.debug(f"Проблемные атрибуты: {list(attrs.keys()) if attrs else 'None'}")
        return None


def test_ldap_connection() -> dict[str, Any]:
    """
    Тестовая функция для проверки LDAP соединения и конфигурации.

    Returns:
        dict с результатами тестирования
    """
    logger.info("=== ЗАПУСК ТЕСТА LDAP СОЕДИНЕНИЯ ===")

    results = {
        "configured": bool(settings.LDAP_URI and settings.LDAP_BASE_DN),
        "uri": settings.LDAP_URI,
        "base_dn": settings.LDAP_BASE_DN,
        "success": False,
        "errors": [],
        "warnings": [],
        "details": {}
    }

    if not results["configured"]:
        results["errors"].append("LDAP не настроен (отсутствует URI или Base DN)")
        logger.warning("LDAP тест не пройден: отсутствует конфигурация")
        return results

    conn = None
    try:
        logger.debug(f"Тестовое подключение к LDAP: {settings.LDAP_URI}")
        conn = ldap.initialize(settings.LDAP_URI)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5.0)
        conn.set_option(ldap.OPT_TIMEOUT, 5.0)
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        # Пробуем анонимную привязку для проверки связи
        try:
            conn.simple_bind_s()
            logger.info("✓ Анонимная привязка к LDAP успешна")
            results["warnings"].append("LDAP сервер позволяет анонимную привязку")
            results["details"]["anonymous_bind"] = True
        except ldap.LDAPError as e:
            logger.debug(f"Анонимная привязка не удалась (ожидаемо для многих AD): {e}")
            results["details"]["anonymous_bind"] = False

        # Проверяем, что Base DN существует
        try:
            result = conn.search_s(
                settings.LDAP_BASE_DN,
                ldap.SCOPE_BASE,
                "(objectClass=*)",
                ["supportedCapabilities"]
            )
            if result:
                logger.info(f"✓ Base DN найден: {settings.LDAP_BASE_DN}")
                results["details"]["base_dn_exists"] = True
                results["success"] = True
            else:
                results["errors"].append(f"Base DN не найден: {settings.LDAP_BASE_DN}")
                results["details"]["base_dn_exists"] = False
        except ldap.NO_SUCH_OBJECT:
            results["errors"].append(f"Base DN не существует: {settings.LDAP_BASE_DN}")
            results["details"]["base_dn_exists"] = False
            logger.error(f"✗ Base DN не существует: {settings.LDAP_BASE_DN}")
        except ldap.LDAPError as e:
            code, msg, _ = _decode_ldap_error(e)
            results["errors"].append(f"Ошибка поиска Base DN: {msg} (код {code})")
            logger.error(f"✗ Ошибка поиска Base DN: {msg}")

    except ldap.SERVER_DOWN as e:
        code, msg, _ = _decode_ldap_error(e)
        results["errors"].append(f"LDAP сервер недоступен: {msg}")
        logger.error(f"✗ LDAP сервер недоступен: {msg}")
    except Exception as e:
        results["errors"].append(f"Неожиданная ошибка: {e}")
        logger.exception(f"✗ Неожиданная ошибка: {e}")
    finally:
        if conn:
            try:
                conn.unbind()
            except:
                pass

    logger.info(f"=== LDAP ТЕСТ ЗАВЕРШЕН: success={results['success']} ===")
    return results