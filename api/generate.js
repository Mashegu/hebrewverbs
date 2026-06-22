export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS, GET");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method === "GET") {
    return res.status(200).json({
      ok: true,
      message: "Hebrew verbs AI API работает",
      endpoints: {
        control: "POST { mode: 'control', ruInf, heInf, ruPast, hePast }",
        full: "POST { mode: 'full', ruInf, heInf, ruPast, hePast, ruPres, hePres, ruFut, heFut, ruImp, heImp }"
      }
    });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Only POST allowed" });
  }

  try {
    const apiKey = process.env.OPENAI_API_KEY;

    if (!apiKey) {
      return res.status(500).json({
        error: "OPENAI_API_KEY не найден в Vercel Environment Variables"
      });
    }

    const body = req.body || {};
    const mode = body.mode || "full";

    const prompt =
      mode === "control"
        ? buildControlPrompt(body)
        : buildFullPrompt(body);

    const openaiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-4.1-mini",
        input: prompt,
        temperature: 0.15,
        text: {
          format: {
            type: "json_object"
          }
        }
      })
    });

    const data = await openaiResponse.json();

    if (!openaiResponse.ok) {
      return res.status(openaiResponse.status).json({
        error: "OpenAI API error",
        details: data
      });
    }

    const text =
      data.output_text ||
      data.output?.[0]?.content?.[0]?.text ||
      "";

    const json = JSON.parse(text);

    return res.status(200).json({
      ok: true,
      mode,
      result: json
    });

  } catch (error) {
    return res.status(500).json({
      error: error.message
    });
  }
}

function buildControlPrompt(body) {
  return `
Ты эксперт по современному ивриту.

Пользователь вводит глагол иврита без огласовок или с огласовками.

Данные пользователя:
перевод инфинитива RU: ${body.ruInf || ""}
инфинитив иврит: ${body.heInf || ""}
перевод прошедшего הוא RU: ${body.ruPast || ""}
прошедшее הוא иврит: ${body.hePast || ""}

Задача:
1. Определи правильный инфинитив с огласовками.
2. Определи прошедшее время הוא с огласовками.
3. Дай контрольные формы:
   - настоящее время הוא
   - будущее время הוא
   - повелительное наклонение ты мужской род
4. Все формы иврита верни только с огласовками.

Верни ТОЛЬКО JSON без markdown:

{
  "heInf": "...",
  "hePast": "...",
  "ruPres": "...",
  "hePres": "...",
  "ruFut": "...",
  "heFut": "...",
  "ruImp": "...",
  "heImp": "..."
}
`;
}

function buildFullPrompt(body) {
  return `
Ты эксперт по современному ивриту.

Создай полную таблицу спряжения глагола иврита.

Проверенные пользователем данные:
перевод инфинитива RU: ${body.ruInf || ""}
инфинитив иврит: ${body.heInf || ""}
перевод прошедшего הוא RU: ${body.ruPast || ""}
прошедшее הוא: ${body.hePast || ""}
перевод настоящего הוא RU: ${body.ruPres || ""}
настоящее הוא: ${body.hePres || ""}
перевод будущего הוא RU: ${body.ruFut || ""}
будущее הוא: ${body.heFut || ""}
перевод повелительного RU: ${body.ruImp || ""}
повелительное ты м.р.: ${body.heImp || ""}

Требования:
1. Все формы иврита обязательно с огласовками.
2. Пользователь может вводить без огласовок, но итоговая таблица должна быть с огласовками.
3. Никаких заглушек.
4. Никаких объяснений.
5. Верни только валидный JSON.
6. Перевод каждой формы должен быть на русском, украинском и английском.

Формат JSON:

{
  "infinitive": "...",
  "translations": {
    "ru": "...",
    "uk": "...",
    "en": "..."
  },
  "searchKeys": {
    "withNiqqud": "...",
    "withoutNiqqud": "..."
  },
  "present": [
    {
      "person": "я / ты / он — м.р.",
      "form": {
        "ru": "...",
        "uk": "...",
        "en": "..."
      },
      "he": "..."
    }
  ],
  "past": [],
  "future": [],
  "imperative": []
}

Количество форм:
present — 4 основные формы:
1. я / ты / он — м.р.
2. я / ты / она — ж.р.
3. мы / вы / они — м.р. мн.ч.
4. мы / вы / они — ж.р. мн.ч.

past — 9 форм:
я, ты м., ты ж., он, она, мы, вы м., вы ж., они

future — 10 форм:
я, ты м., ты ж., он, она, мы, вы м., вы ж., они м., они ж.

imperative — 4 формы:
ты м., ты ж., вы м., вы ж.
`;
}
