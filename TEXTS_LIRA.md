# Тексты интерфейса voice2text (ЛИРА, 15.10)

## 1. Загрузка модели
ru: Скачиваю модель распознавания: {done} из {total} МБ. Это нужно один раз, дальше всё работает прямо на вашем устройстве.
en: Downloading the speech model: {done} of {total} MB. This happens once; after that everything runs on your device.

## 2. Пример без микрофона
ru (кнопка): Попробовать на примере
ru (подпись): Короткая запись синтезированным голосом, чтобы увидеть результат без микрофона. Робота страница понимает хуже, чем живой голос.
(если образец заменят на запись человека с открытой лицензией: «Короткая запись живого голоса с открытой лицензией, чтобы увидеть результат без микрофона.»)
en (button): Try a sample
en (caption): A short clip in a synthesized voice, so you can see the result without a microphone. The page understands a robot worse than a real voice.
(if replaced with an openly licensed human clip: "A short openly licensed clip of a real voice, so you can see the result without a microphone.")

## 3. Отзыв под результатом
ru: Как получилось? Напишите пару слов в issue №1, нам важен каждый честный отзыв.
en: How did it go? Leave a couple of words in issue #1, every honest review helps.

## Плашка приватности
ru: Голос не уходит с вашего устройства. Абзацы расставлены по паузам.
en: Your voice never leaves your device. Paragraphs are split by pauses.

## 5. Открытые вопросы под результатом (15.10, по АРГУСУ и МАРКУ)
- ru: «Что запомнилось?» / en: "What stuck with you?"
- ru: «Чем это лучше того, чем вы пользуетесь сейчас?» / en: "How is this better than what you use now?"
- Подпись под полями, ru: «Пара слов в issue №1, без готовых вариантов» / en: "A few words in issue #1, in your own words"

## 6. Подпись к примеру из FLEURS (замена п.2, 15.10)
- ru: «Пример на живом голосе: зачитанная фраза, одна из удачных. Среднее качество ниже, на вашем голосе может быть иначе. Запись: FLEURS (Google), CC-BY 4.0.» (со ссылкой https://huggingface.co/datasets/google/fleurs)
- en: "A real-voice sample: a read-aloud phrase, one of the better results. Average quality is lower and may differ for your voice. Recording: FLEURS (Google), CC-BY 4.0."

## 7. Выбор модели (15.10, по таблице ГЕФЕСТА)
- ru, по умолчанию: «Быстрая (~80 МБ)» / en: "Fast (~80 MB)"
- ru, опция: «Точнее, но тяжелее (~250 МБ, примерно втрое медленнее)» / en: "More accurate, heavier (~250 MB, about 3× slower)"

## 8. Если основной станет small (по решению МАРКА после отложенного набора)
- ru, по умолчанию: «Точная (~250 МБ, скачивается один раз)» / en: "Accurate (~250 MB, downloaded once)"
- ru, опция: «Быстрая (~80 МБ, ошибается чаще)» / en: "Fast (~80 MB, more mistakes)"
- ru, подсказка при первой загрузке: «Первый запуск дольше: скачиваю модель. На мобильном интернете лучше выбрать „Быструю“.» / en: "First run takes longer while the model downloads. On mobile data, pick „Fast“."

## 9. Сообщение при срабатывании таймаута
- ru: «Точная модель думает слишком долго, поэтому я её остановила. Попробуйте „Быструю“: она справится за секунды, хоть и ошибается чаще. Запись не потерялась.» Кнопка: «Расшифровать быстрой»
- en: "The accurate model is taking too long, so I stopped it. Try „Fast“: it finishes in seconds, though it makes more mistakes. Your recording is still here." Button: "Transcribe with Fast"

## 10. Микрофон
- Подпись полоски громкости: ru «Вас слышно» / en "I can hear you". Показывать, пока идёт запись. Если звука нет, подпись не нужна, тогда работает сообщение о тишине.
- Доступ запрещён:
  - ru: «Браузер не дал доступ к микрофону. Нажмите на значок замка или микрофона слева от адреса страницы и выберите „Разрешить“, затем обновите страницу. На iPhone: Настройки → Safari → Микрофон.»
  - en: "The browser blocked the microphone. Tap the lock or microphone icon left of the page address, choose „Allow“, then reload. On iPhone: Settings → Safari → Microphone."
- Микрофона нет:
  - ru: «Не вижу микрофона. Подключите наушники с микрофоном или откройте страницу на телефоне. А пока можно попробовать на готовом примере ниже.»
  - en: "No microphone found. Plug in a headset or open this page on your phone. Meanwhile, you can try the sample below."
- Тишина дольше 3 с:
  - ru: «Ничего не слышно. Проверьте, какой микрофон выбран, и не выключен ли звук на гарнитуре.»
  - en: "I can't hear anything. Check which microphone is selected and that your headset isn't muted."

## 11. Копирование и вопрос «куда дели текст» (v2.3)

Кнопка: «Скопировать текст» / "Copy text"
Успех (показывать ТОЛЬКО после успешного writeText, 2 с): «Скопировано, вставляйте куда нужно» / "Copied, paste it anywhere"
Ошибка (текст выделен автоматически): «Не получилось скопировать. Текст выделен — скопируйте вручную» / "Couldn't copy. The text is selected, copy it manually"

Вопрос в отзыве: «Куда вы потом дели текст?» / "What did you do with the text?"
- «Вставил в сообщение или документ» / "Pasted it into a message or document"
- «Прочитал и закрыл» / "Read it and closed"
- «Ничего не получилось» / "Nothing worked"

## 12. Подписи во время загрузки модели (v2.3; ЛИРА, R2-20261016, перенесено ГЕФЕСТОМ дословно из proposal_LIRA.md)
- Во время загрузки: «Можно говорить уже сейчас — расшифрую, как только загружусь (N%)» / "You can speak now, I'll transcribe once loaded (N%)"
- Запись готова, модель ещё грузится: «Запись сохранена. Жду модель… N%» / "Recording saved. Waiting for the model… N%"
