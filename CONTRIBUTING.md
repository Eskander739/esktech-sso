# 🤝 Как внести вклад в EskTech SSO

Спасибо за интерес к проекту! Вот как вы можете помочь:

## 🐛 Сообщение об ошибках

1. Проверьте, не сообщал ли уже кто-то об этой ошибке в [Issues](https://github.com/Eskander739/esktech-sso/issues)
2. Если нет — создайте новый issue с шаблоном bug report
3. Опишите:
   - Версию ОС и Python
   - Шаги для воспроизведения
   - Ожидаемое и фактическое поведение
   - Логи ошибок

## 💡 Предложения по улучшению

1. Откройте [Feature Request](https://github.com/Eskander739/esktech-sso/issues/new)
2. Опишите проблему, которую решает ваше предложение
3. Предложите решение

## 🔧 Pull Requests

### Процесс:
```bash
# 1. Форкните репозиторий
# 2. Клонируйте свой форк
git clone https://github.com/YOUR_USERNAME/esktech-sso.git
cd esktech-sso

# 3. Создайте ветку
git checkout -b feature/your-feature-name

# 4. Установите зависимости
pip install -r requirements.txt

# 5. Внесите изменения
# ...

# 6. Запустите тесты
make test

# 7. Проверьте стиль кода
make format
make lint

# 8. Закоммитьте изменения
git commit -m "feat: add your feature description"

# 9. Отправьте изменения
git push origin feature/your-feature-name