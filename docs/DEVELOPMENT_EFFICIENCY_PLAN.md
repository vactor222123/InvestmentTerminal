# План економнішої розробки InvestmentTerminal

## Мета

Менше повторного контексту та ручних handoffs на одну завершену можливість,
без послаблення exact-baseline, privacy, tests та integrity guards.
Це пропозиція процесу, не вже впроваджена зміна AGENTS.md.

## Виміряна проблема

На baseline `53fd2be0153d4842023a16d2286b41b83c971fa7` обов'язкові документи
займають 411 475 байтів, усі Markdown — 1 676 603. Байти НЕ є токенами.
Фактичне token usage не вимірювалося, тому гарантій відсотка загальної економії немає.
Вісімнадцять Current-заголовків у двох handoff-файлах ускладнюють визначення
поточного стану. Значний час витрачається на повторну передачу команд і SHA.

## Зміни процесу за пріоритетом

1. **Один короткий поточний стан.** NEXT_STEPS: один gate, applied baseline,
   останній verified результат, blockers, наступна команда/критерій завершення.
   PROJECT_CONTINUATION: максимум приблизно 100 рядків з посиланнями на evidence.
   Старі записи архівувати без втрати provenance; прибрати слово Current з архіву.
2. **Скоротити mandatory read через явну зміну правил.** Запропонована ціль —
   <=24 KB спільного стартового контексту та читання повних domain-contracts за
   routing table. Це приблизно 94% менше стартових байтів, не обіцянка такої ж
   економії токенів усього сеансу. До погодженої зміни AGENTS/користувацького
   workflow зберігається чинне повне читання; не обходити його самостійно.
3. **Не дублювати package narrative.** Architecture/DataModel містять нормативні
   контракти, Roadmap — capability status; детальний результат пакета записується
   один раз. Нові поточні записи посилаються на нього.
4. **Один пакет = завершений невеликий результат.** Поєднувати 2–3 пов'язані
   audit/implementation/test кроки, якщо не потрібен live evidence gate.
   Одна focused перевірка, один full pytest після завершення змін, один commit.
   Повторювати тести після релевантної зміни, не для незмінного стану.
5. **Використати existing profile runner.** Розвинути weekly_run до перевірених
   операцій validate/run/resume/status, а не генерувати щоразу 200 рядків shell.
   Це запропоновані можливості, не нинішні назви підкоманд. SHA/checksum/privacy
   checks мають жити в тестованому коді. ASCII PowerShell лише запускає його.
6. **Стандартний redacted receipt.** Stage, status, counts, failure category,
   next permitted action, hashes та operation identity. Приватні дані залишаються
   локально. Один receipt замість копіювання великих логів у чат.
7. **Тестований builder пакета.** Fresh clone/exact SHA, explicit changed files,
   перевірка одного commit, ZIP entries/bytes/hash і готові git-команди. Спочатку
   dry-run та failure tests. Не git add ., не автоматичний push.
8. **Читати адресно.** Спочатку індекс і rg, потім потрібні функції/контракти;
   не повторювати величезні truncated outputs. Обов'язкові інструкції все одно
   читати повністю. Інструментальні логи зберігати локально, у контекст — summary.
9. **Новий чат — за handoff, не для втрати історії.** Короткий durable state має
   дозволяти відновлення без сотень старих повідомлень. Без непотрібних паралельних
   агентів і копіювання всього контексту; чинний режим не дозволяє їх без запиту.
10. **Definition of done за capability.** Для weekly: freshness + persistence +
    recovery + receipt; для портфеля: identity + units + splits + quotes + явні
    limitations. Кількість пакетів/тестів сама по собі не є прогресом продукту.

## Що не скорочувати

Fresh clone develop, exact baseline до змін, architecture/dependency guards,
JSON compatibility, focused/failure-path tests, full pytest, diff-check,
один local conventional commit, ZIP + SHA-256, відсутність push, приватність.
Не обходити safety guards, не підмінювати невідомі фінансові дані припущеннями.

## Як перевірити економію

Для наступних 3–5 capability-пакетів фіксувати доступне actual token usage,
прочитані байти, кількість повторних tool outputs, ручних operational handoffs,
повторних тестових прогонів та виправлень shell-команд. Порівнювати на завершену
можливість, а не на commit. Якщо usage недоступне, позначати unknown, не оцінювати
його як bytes/4. Окремо контролювати regression count та час користувача.

Перший процесний пакет: архівувати старі Current-секції, синхронізувати короткі
state/index документи й узгодити routing правила. Не змішувати це з великим
storage rewrite. Детальні технічні пріоритети — у аудиті 2026-10-12.
