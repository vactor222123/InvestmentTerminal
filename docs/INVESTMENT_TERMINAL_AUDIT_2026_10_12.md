# InvestmentTerminal: аудит 2026-10-12

## Follow-up status

A03: bounded prevention implemented from
`95b5265b95fa7ced963d5723814fb196325db5ad`; see `CANDLE_UNIT_SAFETY.md`.
Raw mixed-case labels are rejected and legacy Yahoo GBP successes/requests are
blocked before execution. Both probes are regressions now. Full source-unit
catalog, historical certification, conversion and A07 remain open; no private
data defect or repair is claimed. Earlier status paragraphs are historical.

A02: repository/provider UTC safety implemented from
`f473834faa609db55aedf534881989f13afa5a92`; see `CANDLE_UTC_SAFETY.md`.
Six audit probes promoted to regressions. Incompatible legacy series fail closed;
private corpus inspection/migration and direct-SQL consumer certification are not
claimed. A03 and its two expected-failure probes remain open.

A02/A03: compatibility audit completed at
`67362b6e1cd790858403a28d794f8a4955899835`; see
`CANDLE_TIME_UNIT_COMPATIBILITY.md`. Eight strict expected-failure acceptance
probes expose still-open defects. No production fix or data migration yet.

A01/A04/A05: implemented after this audit, from baseline
`52a9430e6d35e7b350d72d6969337dbf4b9bd987`; see `CANDLE_WRITE_SAFETY.md`.
Local regression evidence only, not verification or repair of private runtime data.
The original findings below remain the historical baseline evidence; other items
remain open, including A02/A03. The old characterization script is baseline-specific.

## Висновок і межі доказів

Baseline: `53fd2be0153d4842023a16d2286b41b83c971fa7`, fresh clone `develop`.
Класифікація пакета: AUDIT, без змін production-коду чи JSON-контрактів.
Продукт має значну працездатну основу, але готовність автоматичного наскрізного
оновлення та split-aware оцінки портфеля ще не доведена. Пріоритет зараз —
захист запису, відновлення та завершення загальних сценаріїв, а не ще один
вузький діагностичний CLI для окремого інструмента.

Проведено інвентаризацію всього tracked-репозиторію, ручний risk-based огляд
критичних маршрутів, повний pytest та п'ять синтетичних відтворень. Це НЕ
построкова формальна верифікація всіх 88 тисяч рядків, penetration test або
сертифікація приватної бази. Приватні CSV, snapshots, cache та SQLite не читалися;
провайдери не викликалися. Наявність дефекту API не доводить пошкодження live-даних.

Інвентар baseline: 1 298 tracked-файлів; 472 production Python-файли;
88 410 source-рядків (текстовий підрахунок, не logical LOC); 477 тестових Python-файлів;
85 CLI-модулів без `__init__`; 325 Markdown-файлів, 1 676 603 байти.

## Реєстр недоліків

P1 — першочергова цілісність/готовність даних; P2 — наступна функціональна чи
операційна робота; P3 — підтримуваність. «Відтворено» означає локальний synthetic
proof, «прогалина» — відсутню інтеграцію/контракт, «ризик» — наслідок ще не виміряно.

### A01 · P1 · Відтворено: конфлікт свічки мовчки приймається за повтор

`investment_terminal/repositories/candle_repository.py`: `save_many` використовує
`INSERT OR IGNORE`; `save` після IntegrityError повертає existing ID за ключем.
Той самий ключ з іншим close/currency не відрізняється від ідентичного повтору.
Weekly-сервіс має додаткову перевірку drift, але це не універсальний repository guard.
Прийняття виправлення: exact replay = no-op; змінений payload = typed conflict;
жодного мовчазного overwrite; тести обох save API і змішаного batch.

### A02 · P1 · Відтворено: час не канонізовано

Той самий repository зберігає `timestamp.isoformat()` без UTC-нормалізації,
приймає naive datetime. Один instant з UTC та +01:00 утворює два рядки;
range queries порівнюють текст. Прийняття: явний timezone contract, UTC key,
відхилення naive input, перевірки меж та дублювання; окремий read-only план
перевірки старих даних до будь-якої міграції.

### A03 · P1 · Відтворено: minor-unit позначення губиться

Repository застосовує `.upper()` до currency: `GBp` стає `GBP`, ціна не масштабується.
Це небезпечне ототожнення пенсів і фунтів для такого input, не доказ помилки
поточного universe. Прийняття: відхиляти непідтриману одиницю або явно
нормалізувати currency + unit + value на adapter boundary; тест відсутності
непомітної зміни економічного значення.

### A04 · P1 · Відтворено: batch failure лишає незавершені записи

`save_many` не відкочує транзакцію після SQLite-помилки посеред executemany.
Синтетичний trigger зупинив другий insert; перший лишився в транзакції та був
закомічений наступним успішним save. Прийняття: атомарність batch і визначений
ownership транзакції, failure injection та перевірка наступної операції.

### A05 · P1 · Відтворено: error report може знищити input

`investment_terminal/cli/weekly_candle_refresh.py`: preflight виявляє однакові
шляхи manifest/report, але загальний except створює FAILED payload, після чого
безумовний writer записує його саме поверх manifest. Відтворено лише на
тимчасовому synthetic-файлі, без provider call. Новіший `weekly_run` має
додаткові guards; висновок стосується прямого CLI, а не кожного weekly run.
Прийняття: output safety до будь-якого writer, включно з failure path;
collision matrix для всіх inputs/outputs, existing outputs та alias paths.

### A06 · P1 · Прогалина: backup coverage не охоплює основний market runtime

`persistence/sqlite_inventory.py`, `runtime_backup_service.py`: typed backup
boundaries охоплюють history/knowledge/usage/generation, але не повний комплект
candles + portfolio ledger + manifests/checkpoints + action evidence.
Зовнішній backup користувача не перевірявся. Прийняття: явний consistent backup
набір, restore у новий каталог, integrity та checkpoint/data reconciliation;
не копіювати відкриту SQLite навмання. Зберегти вже наявні staging/atomic guards.

### A07 · P1 · Прогалина: недостатньо provenance/price-basis для коригувань

`database/schema.py` candles не містить source, price basis, revision чи action
binding. Yahoo adapter запитує `auto_adjust=False`, але це не універсальний
доказ економічної бази кожної історичної серії. Raw indicator export правильно
декларує відсутність explicit adjustment. Прийняття: документований, перевірений
source basis та immutable зв'язок з actions до adjusted SMA/returns; захист
від подвійного split adjustment. Не оголошувати наявні raw дані неправильними.

### A08 · P1 · Прогалина: split projection не завершена наскрізно

`portfolio/split_projection.py` реалізує detached projection та строгий збіг
symbol/currency/type. `portfolio/transaction_derived_valuation.py` не використовує
її. Навіть provider listing, знайдений під іншим ticker, не можна просто передати
через цей strict guard. Прийняття: typed identity mapping + split-aware valuation
з точним порядком подій, fractional quantities, unchanged ledger та cost basis;
unknown mapping/basis лишаються blockers, без guessed identity.

### A09 · P2 · Прогалина: автоматична оцінка портфеля ще не є єдиним маршрутом

`cli/transaction_derived_valuation.py` вимагає `--quotes` JSON. Наявність окремих
market providers не дорівнює їх інтеграції в цей workflow. Прийняття: користувач
вносить операції, quotes отримуються автоматично з provenance/freshness;
непідтримані інструменти, FX, fees і cash відображаються як явні обмеження,
а не вигадані повні прибутки. Dividends/total return — окремі acceptance gates.

### A10 · P2 · Підтверджений blocker: resolver потребує existing ticker

`cli/portfolio_split_resolve.py` після ISIN search вимагає exact existing ticker.
Дозволений redacted report `portfolio_split_symbol_resolution_20261010_162731_0939c947.json`
має BLOCKED/MISSING_EXISTING_TICKER, один search/candidate, нуль action calls.
SHA-256 звіту: `f36ec29bafdcdb3e06b68f88886d261a8c38b8af0f2f547beaa9aa965d24ada1`.
Прийняття: загальний evidence-bound mapping workflow, не зміна broker CSV;
один результат пошуку сам собою не сертифікує broker/provider identity.
Незавершена чернетка в іншому clone не входить до цього baseline чи пакета.

### A11 · P2 · Прогалина: короткий weekly runner не закриває весь lifecycle

`cli/weekly_run.py` вже скорочує запуск через profile — не потрібно винаходити
другу таку обгортку. Але refresh, quality, indicators, export та integrity receipts
залишаються окремими операціями. Прийняття: один profile-backed запуск з видимими
стадіями, resume, progress і фінальним factual readiness report; UI потім викликає
той самий service, а не копіює PowerShell.

### A12 · P2 · Прогалина: freshness/coverage не тотожні SUCCESS

`operations/weekly_candle_refresh.py` має 7-day overlap та 90-day window bound;
непорожня відповідь не гарантує актуальний tail. Stored sample counts не доводять
session completeness для всіх бірж. Прийняття: окремі transport/persistence/
freshness/session статути, довгі gaps з bounded recovery, IPO/delisted/calendar
limitations без false completeness. Не скасовувати існуючі fail-closed checks.

### A13 · P2 · Прогалина: класифіковане відновлення неповне

Weekly retry спеціально відкриває rate-limit outcomes; інші terminal failures
не отримують такого самого явного retry маршруту. Drift може блокувати і new tail.
Прийняття: policy за типом помилки, bounded backoff/circuit breaker, окремі data
revisions і retry; незмінні good outcomes не перезавантажувати без причини.

### A14 · P2 · Ризик: немає єдиного concurrency/migration контракту

Weekly wrapper має exclusive lock; прямий CLI не має еквівалентного common guard.
Empty lockfile після hard kill не несе owner/run metadata. `database/database.py`
ініціалізує schema без явного versioned migration lifecycle. Конкурентне
пошкодження не відтворювалося. Прийняття: спільний lock ownership/recovery,
schema version + backup-aware migrations і subprocess/crash тести.

### A15 · P3 · Ризик продуктивності: повний checkpoint переписується на item

Серіалізація growing outcomes після кожного item дає сумарну роботу порядку
1+2+...+N. Реальний bottleneck не виміряний. Спочатку benchmark часу/network/
serialization/fsync, потім incremental journal або інше bounded рішення з
crash-recovery parity; не оптимізувати на припущеннях.

### A16 · P2 · Прогалина: Windows delivery недостатньо тестується

CI перевіряє Linux/container, але не повний користувацький Windows PowerShell 5.1
runner. Історичні помилки quoting, Split-Path, IsFinite та numeric property names
узгоджуються з цією прогалиною. Прийняття: executable ASCII runner, Windows CI,
argv/path/space/Unicode filesystem tests; не надсилати щоразу нові великі блоки.

### A17 · P2 · Прогалина тестів: зелений suite не покриває storage safety

Усі п'ять probes відтворилися поряд із зеленими 3 713 тестами. Прийняття:
regression tests A01–A05, property tests time/unit/idempotence, fault injection
commit/report/checkpoint, end-to-end synthetic lifecycle. Coverage/mutation gate
у поточному CI не встановлено; відсоток покриття цим аудитом не вимірювався.

### A18 · P2 · Прогалина privacy guard

`repository_privacy_audit.py` переважно перевіряє очікувані ignore literals і
обмежений набір файлів: це не повний tracked-secret scanner. `.pytest-total-audit-*`
залишилися untracked, тому `git add .` небезпечний. Реального витоку не знайдено.
Прийняття: перевірка tracked paths/forbidden artifacts, tested ignore semantics,
explicit staging, synthetic fixtures; не читати private inputs для такого тесту.

### A19 · P3 · Архітектурний борг CLI composition

12 CLI-файлів імпортують peer CLI; 49 містять broad except (саме число не доводить
помилку). Generic PRECONDITION_OR_RUNTIME_FAILURE може приховувати стадію причини.
Прийняття: shared operation services і typed safe diagnostics лише для реальних
повторів; architecture guards лишаються. Не переписувати 85 CLI одночасно.

### A20 · P2 · Прогалина життєвого циклу universe

Weekly plan спирається на successes початкового manifest; це не автоматичне
додавання IPO чи повторна кваліфікація виключень. Прийняття: versioned membership,
scheduled policy review exclusions, окремі backfill/current refresh, stable IDs.
Це не вимога мати саме склад S&P 500.

### A21 · P2 · Документація перевантажена і суперечлива

Обов'язковий набір 13 документів: 411 475 байтів / 8 258 текстових рядків.
У PROJECT_CONTINUATION та NEXT_STEPS разом 18 заголовків Current; AI_CONTEXT та
PROJECT_STATUS містять старі sprint milestones. Прийняття: один current gate,
архів історії, short routing + domain contracts; план у DEVELOPMENT_EFFICIENCY_PLAN.
Цей audit лише додає актуальний gate, не робить прихованого великого переписування.

### A22 · P2 · Процес оптимізує пакети, а не завершені можливості

Багато окремих diagnostic/report/SHA handoffs збільшують context і ручну роботу.
Прийняття: capability acceptance checklist, 2–3 пов'язані кроки в одному пакеті,
один verification pass і один commit; зупинка лише на нових фактичних evidence
або authority gates. Не розширювати дозволи під приводом оптимізації.

### A23 · P3 · Продуктова межа потребує явного розділення

Legacy recommendation/DecisionEngine функції існують поряд із factual pipeline
(`services/analysis_orchestrator.py`, `cli/portfolio_ranking.py`). Бажаний продукт
збирає факти для зовнішнього ChatGPT. Прийняття: позначити decision features
optional/legacy, не змішувати їх висновки з factual exports; не видаляти їх навмання.

### A24 · P2 · Ризики, що потребують окремої перевірки

Не проведено актуальний dependency vulnerability scan, provider licensing audit,
runtime ACL/TLS pentest, production concurrency/load test чи live restore drill.
Не оголошувати ці області ані безпечними, ані дефектними без доказів. Acceptance:
окремі scoped перевірки з дозволами й redacted evidence; поточний pip check
перевіряє залежності, а не відсутність CVE.

## Що зберегти

Dependency/architecture guards, pinned hashed dependencies, immutable evidence,
checkpoint bindings, deterministic projections, redaction, bounded network calls,
raw-indicator limitations, існуючі backup staging/atomicity та authentication tests.
Вони корисні; їх не слід прибирати заради меншої кількості рядків чи токенів.

## Перевірки

- Focused: 222 passed, 15.54 s; repository, weekly, split, ledger, architecture,
  dependencies, research verification, backup/restore, privacy, authentication.
- Full baseline: 3 713 passed, 4 skipped, 42.19 s; фінальний повтор після додавання
  audit artifacts: 3 713 passed, 4 skipped, 38.68 s. Один наявний Starlette warning.
- `git diff --check` та staged diff-check: clean.
- Skips: два directory fsync Windows cases та два unavailable symlink cases.
- `python -m pip check`: No broken requirements found.
- A01–A05: п'ять synthetic reproductions; `python docs/audits/reproduce_20261012.py`.
  Це characterization дефектів baseline, НЕ тести бажаної поведінки; після
  виправлення їх asserts мають перестати проходити. Production regression tests
  повинні перевіряти протилежні, безпечні результати в implementation-пакеті.
- Live provider/SQLite integrity/реальний portfolio correctness: НЕ запускалися.

## Послідовність наступних пакетів

1. A05 + A01/A04: захист outputs і атомарний conflict-aware storage, з regression tests.
2. A02/A03/A07: час, одиниці та provenance; спочатку contracts і migration audit.
3. A06/A11/A13/A16: backup/restore та один weekly lifecycle runner.
4. A08–A10: загальний identity + split-aware valuation, потім qualification.

Документаційне скорочення A21/A22 можна виконати окремим малим пакетом перед
цими роботами. Автоматичне застосування виправлень цим аудитом не санкціоноване.
