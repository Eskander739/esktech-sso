import logging
import logging.handlers
import os
from datetime import UTC, datetime
from pathlib import Path


class DefaultLogger:
    """
    Конфигурация системы логирования
    """

    def __init__(self, name: str = "Backend", log_dir: str = "/var/log/backend"):
        """
        Инициализация логгера

        Args:
            name: Имя логгера
            log_dir: Директория для хранения логов
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Очищаем существующие обработчики
        self.logger.handlers.clear()

        # Создаем форматтер
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Файловый обработчик
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            log_file = Path(
                os.path.join(log_dir, f"backend_{datetime.now(UTC).strftime('%Y%m')}.log")
            )
            if not log_file.is_dir():
                log_file.touch(exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file), maxBytes=10 * 1024 * 1024, backupCount=5  # 10 MB
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        except Exception as err:
            self.logger.warning(f"Ошибка при настройке файлового логирования: {err}")

    def info(self, message: str, *args, **kwargs):
        """Логирование информационного сообщения"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Логирование предупреждения"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Логирование ошибки"""
        self.logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Логирование отладочной информации"""
        self.logger.debug(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Логирование критической ошибки"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, exc_info: bool = True, *args, **kwargs):
        """Логирование исключения с трассировкой"""
        self.logger.exception(message, exc_info=exc_info, *args, **kwargs)


# Глобальный экземпляр логгера
logger = DefaultLogger()
