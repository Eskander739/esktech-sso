import gettext

from config import settings
from fastapi import Request


class LocalizationService:
    def __init__(self, locales_dir: str = "src/locale"):
        self.locales_dir = locales_dir
        self.default_locale = settings.LOCALE_DEFAULT
        self.domain = "messages"
        self.translations: dict[str, gettext.NullTranslations] = {}

    def get_translator(self, locale: str) -> gettext.NullTranslations:
        locale = locale or self.default_locale

        if locale not in self.translations:
            try:
                translation = gettext.translation(
                    self.domain, self.locales_dir, languages=[locale], fallback=True
                )
                self.translations[locale] = translation
            except FileNotFoundError:
                self.translations[locale] = gettext.NullTranslations()

        return self.translations[locale]

    def gettext(self, text: str, locale: str) -> str:
        translator = self.get_translator(locale)
        return translator.gettext(text)


localization = LocalizationService()


def _(text: str, request: Request | None = None) -> str:
    if request and hasattr(request.state, "locale"):
        locale = request.state.locale
    else:
        locale = None

    return localization.gettext(text, locale)