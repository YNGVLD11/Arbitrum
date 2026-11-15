"""
Модуль валидации документов на соответствие техническим требованиям
сервиса «Почта России — Электронные заказные письма» (zakaznoe.pochta.ru).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
import pypdf


@dataclass
class ValidationResult:
    """Результат проверки документа на соответствие правилам сервиса."""
    is_valid: bool
    file_path: str
    file_size_bytes: int
    page_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def file_size_mb(self) -> float:
        """Возвращает размер файла в мегабайтах."""
        return self.file_size_bytes / (1024 * 1024)


class RussianPostValidator:
    """
    Валидатор файлов для отправки через сервис zakaznoe.pochta.ru.
    Реализует строгую проверку ограничений платформы:
    - Максимальный размер файла: 20 МБ
    - Максимальное число страниц для бумажной доставки: 19
    - Формат страниц: строго А4 книжной ориентации (210 x 297 мм)
    - Отсутствие паролей и повреждений структуры PDF
    """

    MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024
    MAX_PAPER_PAGES: int = 19

    A4_WIDTH_PT: float = 595.28
    A4_HEIGHT_PT: float = 841.89
    TOLERANCE_PT: float = 4.0

    @classmethod
    def validate_pdf(cls, file_path: str) -> ValidationResult:
        """
        Выполняет комплексную проверку PDF-файла.

        Args:
            file_path: Абсолютный путь к файлу.

        Returns:
            ValidationResult с перечнем ошибок и предупреждений.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not os.path.isfile(file_path):
            return ValidationResult(
                is_valid=False,
                file_path=file_path,
                file_size_bytes=0,
                page_count=0,
                errors=["Файл не найден по указанному пути."]
            )

        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_FILE_SIZE_BYTES:
            errors.append(
                f"Размер файла {file_size / (1024 * 1024):.2f} МБ превышает допустимый лимит 20 МБ."
            )

        if not file_path.lower().endswith(".pdf"):
            errors.append("Для автоматической проверки структуры поддерживается только формат PDF.")
            return ValidationResult(
                is_valid=len(errors) == 0,
                file_path=file_path,
                file_size_bytes=file_size,
                page_count=0,
                errors=errors,
                warnings=warnings
            )

        try:
            reader = pypdf.PdfReader(file_path)
        except Exception as exc:
            errors.append(f"Ошибка чтения структуры PDF-документа: {exc}")
            return ValidationResult(
                is_valid=False,
                file_path=file_path,
                file_size_bytes=file_size,
                page_count=0,
                errors=errors
            )

        if reader.is_encrypted:
            errors.append("Документ защищен паролем. Сервис не принимает зашифрованные файлы.")

        page_count = len(reader.pages)
        if page_count == 0:
            errors.append("Документ не содержит страниц.")
        elif page_count > cls.MAX_PAPER_PAGES:
            warnings.append(
                f"В документе {page_count} страниц. При доставке письма на бумаге лимит составляет 19 страниц."
            )

        for index, page in enumerate(reader.pages, start=1):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            if width > height:
                errors.append(
                    f"Страница {index}: альбомная ориентация {width * 25.4 / 72:.1f} x {height * 25.4 / 72:.1f} мм. "
                    f"Требуется книжный формат А4 (210 x 297 мм)."
                )
                continue

            width_diff = abs(width - cls.A4_WIDTH_PT)
            height_diff = abs(height - cls.A4_HEIGHT_PT)

            if width_diff > cls.TOLERANCE_PT or height_diff > cls.TOLERANCE_PT:
                errors.append(
                    f"Страница {index}: размер {width * 25.4 / 72:.1f} x {height * 25.4 / 72:.1f} мм "
                    f"отличается от формата А4 (210 x 297 мм)."
                )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            file_path=file_path,
            file_size_bytes=file_size,
            page_count=page_count,
            errors=errors,
            warnings=warnings
        )
