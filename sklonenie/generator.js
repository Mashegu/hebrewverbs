(function () {
  "use strict";

  const STORAGE_KEY = "tables3_generated_v1";

  const PERSON_ORDER = [
    "1s", "2ms", "2fs", "3ms", "3fs",
    "1p", "2mp", "2fp", "3mp", "3fp"
  ];

  const PERSON_LABELS = {
    "1s": "я",
    "2ms": "ты м.",
    "2fs": "ты ж.",
    "3ms": "он",
    "3fs": "она",
    "1p": "мы",
    "2mp": "вы м.",
    "2fp": "вы ж.",
    "3mp": "они м.",
    "3fp": "они ж."
  };

  const PERSON_PRONOUNS = {
    ru: {
      "1s": "я",
      "2ms": "ты",
      "2fs": "ты",
      "3ms": "он",
      "3fs": "она",
      "1p": "мы",
      "2mp": "вы",
      "2fp": "вы",
      "3mp": "они",
      "3fp": "они"
    },
    uk: {
      "1s": "я",
      "2ms": "ти",
      "2fs": "ти",
      "3ms": "він",
      "3fs": "вона",
      "1p": "ми",
      "2mp": "ви",
      "2fp": "ви",
      "3mp": "вони",
      "3fp": "вони"
    },
    en: {
      "1s": "me",
      "2ms": "you",
      "2fs": "you",
      "3ms": "him",
      "3fs": "her",
      "1p": "us",
      "2mp": "you",
      "2fp": "you",
      "3mp": "them",
      "3fp": "them"
    }
  };

  function ensureGlobals() {
    window.TABLES = window.TABLES || {};
    window.TABLES2 = window.TABLES2 || {};
    window.TABLES3 = window.TABLES3 || {};
  }

  function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function stripNiqqud(s) {
    return String(s || "")
      .normalize("NFC")
      .replace(/[\u0591-\u05C7]/g, "");
  }

  function normalizeSpaces(s) {
    return String(s || "").replace(/\s+/g, " ").trim();
  }


function normalizeForCompare(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[\u0591-\u05C7]/g, "") // убираем никуд (иврит)
    .replace(/[׳']/g, "")
    .replace(/[‐-‒–—−-]/g, " ") // все дефисы → пробел
    .replace(/[\/=,:;.!?()[\]{}"'`«»„“”<>\\|@#$%^&*_+]/g, " ") // знаки → пробел
    .replace(/\s+/g, " ") // несколько пробелов → один
    .trim();
}

  function detectLanguage(term) {
    const raw = normalizeSpaces(term);
    if (!raw) return "unknown";

    if (/[\u0590-\u05FF]/.test(raw)) return "he";
    if (/[іїєґІЇЄҐ]/.test(raw)) return "uk";
    if (/[а-яёА-ЯЁ]/.test(raw)) return "ru";
    if (/[a-zA-Z]/.test(raw)) return "en";

    return "unknown";
  }

  function getAllTablesMerged() {
    ensureGlobals();
    return Object.assign({}, window.TABLES || {}, window.TABLES3 || {});
  }

  function findEntryInObject(term, obj, sourceName) {
    const q = normalizeForCompare(term);
    if (!q || !obj) return null;
    for (const [key, entry] of Object.entries(obj)) {
      const variants = buildSearchVariants(key, entry);
      if (variants.includes(q)) {
        return { key, entry, source: sourceName };
      }
    }
    return null;
  }

  function findEntryInTablesOnly(term) {
    ensureGlobals();
    return findEntryInObject(term, window.TABLES || {}, "tables");
  }

  function findEntryInGeneratedOnly(term) {
    ensureGlobals();
    return findEntryInObject(term, window.TABLES3 || {}, "tables3");
  }

  function findEntryInTables2Only(term) {
    ensureGlobals();
    return findEntryInObject(term, window.TABLES2 || {}, "tables2");
  }

  function saveTABLES2ToStorage() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(window.TABLES3 || {}, null, 2)
    );
  }

  function loadTABLES2FromStorage() {
    ensureGlobals();

    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        window.TABLES3 = Object.assign({}, window.TABLES3 || {}, parsed);
      }
    } catch (e) {
      console.warn("TABLES2 parse error:", e);
    }
  }

  function mergeGeneratedIntoTables() {
    ensureGlobals();
    return window.TABLES3 || {};
  }

  function makeSafeKey(s) {
    const key = normalizeSpaces(stripNiqqud(s))
      .toLowerCase()
      .replace(/[^\u0590-\u05ffa-zа-яёіїєґ0-9]+/gi, "_")
      .replace(/^_+|_+$/g, "");

    return key || ("generated_" + Date.now());
  }

  function buildSearchVariants(entryKey, entry) {
    const out = new Set();

    out.add(entryKey);

    if (entry?.base) {
      out.add(entry.base.he || "");
      out.add(entry.base.ru || "");
      out.add(entry.base.uk || "");
      out.add(entry.base.en || "");
    }

    if (Array.isArray(entry?.forms)) {
      entry.forms.forEach((f) => {
        out.add(f?.form || "");
        out.add(f?.tr?.ru || "");
        out.add(f?.tr?.uk || "");
        out.add(f?.tr?.en || "");
      });
    }

    if (entry?.aliases) {
      ["he", "ru", "uk", "en"].forEach((lang) => {
        const arr = entry.aliases[lang];
        if (Array.isArray(arr)) {
          arr.forEach((x) => out.add(x || ""));
        }
      });
    }

    return Array.from(out)
      .map(normalizeForCompare)
      .filter(Boolean);
  }

  function findEntryEverywhere(term) {
    const q = normalizeForCompare(term);
    if (!q) return null;

    const all = getAllTablesMerged();

    for (const [key, entry] of Object.entries(all)) {
      const variants = buildSearchVariants(key, entry);
      if (variants.includes(q)) {
        return { key, entry, source: window.TABLES3[key] ? "tables3" : "tables" };
      }
    }

    return null;
  }

  const INDECLINABLE_TERMS = new Set([
    "כאן", "פה", "שם", "עכשיו", "מאוד", "פתאום", "כמעט",
    "אורז", "זהב", "חלב", "מים", "אוויר", "חול", "פחם", "עשן", "אבק", "קרח", "סוכר", "מלח",
    "רק", "כבר", "שוב", "פשוט", "אולי", "אף פעם",
    "песок", "вода", "воздух", "свет", "уголь", "дым", "пыль", "лёд", "лед", "сахар", "соль",
    "пісок", "повітря", "вугілля", "дим", "пил", "лід", "цукор", "сіль",
    "sand", "water", "air", "light", "coal", "smoke", "dust", "ice", "sugar", "salt"
  ].map(normalizeForCompare));

  function isLikelyIndeclinable(term) {
    const q = normalizeForCompare(term);
    if (!q) return false;
    if (INDECLINABLE_TERMS.has(q)) return true;
    if (findEntryInTables2Only(term)) return true;

    const frozenPatterns = [
      /^כאן$/, /^פה$/, /^שם$/, /^עכשיו$/, /^מאוד$/, /^פתאום$/, /^כמעט$/,
      /^רק$/, /^כבר$/, /^שוב$/, /^פשוט$/, /^אולי$/, /^אף פעם$/
    ];
    return frozenPatterns.some((re) => re.test(q));
  }

  function autoDetectNotDeclinable(inputTerm, heWord) {
    const he = normalizeForCompare(heWord || "");
    const term = normalizeForCompare(inputTerm || "");

    const semanticHe = new Set([
      "מוך", "טחב", "אזוב", "אוויר", "מים", "חול", "אור", "פחם", "עשן", "אבק", "קרח", "סוכר", "מלח"
    ]);
    const semanticRu = new Set([
      "пух", "мох", "воздух", "вода", "песок", "свет", "уголь", "дым", "пыль", "лёд", "лед", "сахар", "соль"
    ]);
    const semanticUk = new Set([
      "пух", "мох", "повітря", "вода", "пісок", "світ", "вугілля", "дим", "пил", "лід", "цукор", "сіль"
    ]);
    const semanticEn = new Set([
      "down", "fluff", "moss", "air", "water", "sand", "light", "coal", "smoke", "dust", "ice", "sugar", "salt"
    ]);

    if (isLikelyIndeclinable(he) || isLikelyIndeclinable(term)) return true;
    if (semanticHe.has(he) || semanticRu.has(term) || semanticUk.has(term) || semanticEn.has(term)) return true;

    const exactHe = heWord ? findEntryEverywhere(heWord) : null;
    if (exactHe && exactHe.entry) return false;

    return false;
  }

  function findEntriesByBaseTranslation(term, lang) {
    const q = normalizeForCompare(term);
    const all = getAllTablesMerged();
    const results = [];

    for (const [key, entry] of Object.entries(all)) {
      const val = normalizeForCompare(entry?.base?.[lang] || "");
      if (val && val === q) {
        results.push({ key, entry });
      }

      const aliases = entry?.aliases?.[lang];
      if (Array.isArray(aliases)) {
        const hit = aliases.some((a) => normalizeForCompare(a) === q);
        if (hit) {
          results.push({ key, entry });
        }
      }
    }

    return results;
  }

  function getModelPriority() {
    return [
      "lifnei_like",
      "etzel_like",
      "im_like",
      "el_like",
      "al_like",
      "tahat_like",
      "betoch_like",
      "mul_like",
      "leyad_like"
    ];
  }

  function inferModelFromHebrew(heWord) {
    const raw = normalizeSpaces(heWord);
    const clean = stripNiqqud(raw);
    if (!clean) return null;

    if (clean === "לפני" || clean === "אחרי") return "lifnei_like";
    if (clean === "אצל") return "etzel_like";
    if (clean === "עם") return "im_like";
    if (clean === "אל") return "el_like";
    if (clean === "על") return "al_like";
    if (clean === "תחת") return "tahat_like";
    if (clean === "בתוך") return "betoch_like";
    if (clean === "מול") return "mul_like";
    if (clean === "ליד") return "leyad_like";

    if (/י$/.test(clean)) return "lifnei_like";
    if (/וך$/.test(clean)) return "betoch_like";
    if (/ת$/.test(clean)) return "tahat_like";
    if (/ל$/.test(clean)) return "etzel_like";
    if (/ם$/.test(clean)) return "im_like";

    return null;
  }

  function getFormsWithPersons(entry) {
    if (!entry || !Array.isArray(entry.forms)) return [];
    return entry.forms.map((f, index) => ({
      ...f,
      person: f?.person || PERSON_ORDER[index] || null,
      _index: index
    })).filter((f) => f.person);
  }

  function getHebrewPatternSignature(s) {
    const raw = normalizeSpaces(String(s || "")).normalize("NFC");
    if (!raw) return "";
    return Array.from(raw).map((ch) => /[֑-ׇ]/.test(ch) ? "N" : "L").join("");
  }

function rawIndexForLetterPos(raw, pos) {
  const chars = Array.from(String(raw || "").normalize("NFC"));
  if (pos <= 0) return 0;
  let letterCount = 0;
  for (let i = 0; i < chars.length; i++) {
    if (!/[\u0591-\u05C7]/.test(chars[i])) {
      if (letterCount === pos) return i;
      letterCount += 1;
      if (letterCount === pos && i === chars.length - 1) return chars.length;
    }
  }
  return chars.length;
}

function splitAroundBaseWithNiqqud(rawForm, rawBase) {
  const form = String(rawForm || "").normalize("NFC");
  const base = String(rawBase || "").normalize("NFC");
  const formNoNiq = stripNiqqud(form);
  const baseNoNiq = stripNiqqud(base);
  if (!formNoNiq || !baseNoNiq) return null;

  const idx = formNoNiq.indexOf(baseNoNiq);
  if (idx < 0) return null;

  const startRaw = rawIndexForLetterPos(form, idx);
  const endRaw = rawIndexForLetterPos(form, idx + baseNoNiq.length);

  return {
    prefix: form.slice(0, startRaw),
    matched: form.slice(startRaw, endRaw),
    suffix: form.slice(endRaw)
  };
}


function getSuffixProfile(entry) {
  const forms = getFormsWithPersons(entry);
  const baseHe = normalizeSpaces(entry?.base?.he || "");
  const baseNoNiq = stripNiqqud(baseHe);
  if (!baseNoNiq || forms.length !== PERSON_ORDER.length) return null;

  const profile = [];
  for (const person of PERSON_ORDER) {
    const formObj = forms.find((f) => f.person === person);
    if (!formObj?.form) return null;
    const form = normalizeSpaces(String(formObj.form));
    const parts = splitAroundBaseWithNiqqud(form, baseHe);
    if (!parts) return null;
    profile.push({
      person,
      prefix: parts.prefix,
      suffix: parts.suffix
    });
  }
  return profile;
}

  function getStrictnessReport(term, entry) {
    const input = normalizeSpaces(String(term || ""));
    const inputNoNiq = stripNiqqud(input);
    const baseHe = normalizeSpaces(entry?.base?.he || "");
    const baseNoNiq = stripNiqqud(baseHe);
    const forms = getFormsWithPersons(entry);
    const suffixProfile = getSuffixProfile(entry);
    if (!inputNoNiq || !baseNoNiq || forms.length !== PERSON_ORDER.length || !suffixProfile) return null;

    const sameLetters = inputNoNiq.length === baseNoNiq.length;
    const samePattern = getHebrewPatternSignature(input) === getHebrewPatternSignature(baseHe);
    const sameEnding = inputNoNiq.slice(-1) === baseNoNiq.slice(-1);
    const sameEnding2 = inputNoNiq.slice(-2) === baseNoNiq.slice(-2);

    let score = 0;
    if (sameLetters) score += 5;
    if (samePattern) score += 5;
    if (sameEnding) score += 2;
    if (sameEnding2) score += 3;

    return {
      sameLetters,
      samePattern,
      sameEnding,
      sameEnding2,
      hasFullSuffixSet: true,
      score,
      suffixProfile
    };
  }

  function findBestAnalog(term, lang) {
    const all = getAllTablesMerged();
    const entries = Object.entries(all).map(([key, entry]) => ({ key, entry }));

    if (lang === "he") {
      const exactHe = entries.find(
        (x) => normalizeForCompare(x.entry?.base?.he || "") === normalizeForCompare(term)
      );
      if (exactHe) return exactHe;

      const inferredModel = inferModelFromHebrew(term);
      const scored = entries
        .map((x) => ({ ...x, report: getStrictnessReport(term, x.entry) }))
        .filter((x) => x.report);

      const strict = scored
        .filter((x) => x.report.sameLetters && x.report.samePattern)
        .sort((a, b) => {
          if ((b.report.sameEnding2 ? 1 : 0) !== (a.report.sameEnding2 ? 1 : 0)) {
            return (b.report.sameEnding2 ? 1 : 0) - (a.report.sameEnding2 ? 1 : 0);
          }
          if ((b.entry?.model === inferredModel ? 1 : 0) !== (a.entry?.model === inferredModel ? 1 : 0)) {
            return (b.entry?.model === inferredModel ? 1 : 0) - (a.entry?.model === inferredModel ? 1 : 0);
          }
          return b.report.score - a.report.score;
        });

      if (strict.length) return strict[0];
      return null;
    }

    if (lang === "ru" || lang === "uk" || lang === "en") {
      const byTranslation = findEntriesByBaseTranslation(term, lang);
      if (byTranslation.length) return byTranslation[0];
      return null;
    }

    return null;
  }

  function inferNounGender(baseWord, lang) {
    const word = normalizeSpaces(String(baseWord || "")).toLowerCase();
    if (!word) return "m";

    if (lang === "ru") {
      if (/(ы|и)$/.test(word)) return "pl";
      if (/(о|е|ё)$/.test(word)) return "n";
      if (/(а|я|ь)$/.test(word)) return "f";
      return "m";
    }

    if (lang === "uk") {
      if (/(и|ї)$/.test(word)) return "pl";
      if (/(о|е|є)$/.test(word)) return "n";
      if (/(а|я|ь)$/.test(word)) return "f";
      return "m";
    }

    return "any";
  }

  function getPossessivePronoun(person, lang, nounGender) {
    const map = {
      ru: {
        m: {"1s":"мой","2ms":"твой","2fs":"твой","3ms":"его","3fs":"её","1p":"наш","2mp":"ваш","2fp":"ваш","3mp":"их","3fp":"их"},
        f: {"1s":"моя","2ms":"твоя","2fs":"твоя","3ms":"его","3fs":"её","1p":"наша","2mp":"ваша","2fp":"ваша","3mp":"их","3fp":"их"},
        n: {"1s":"моё","2ms":"твоё","2fs":"твоё","3ms":"его","3fs":"её","1p":"наше","2mp":"ваше","2fp":"ваше","3mp":"их","3fp":"их"},
        pl:{"1s":"мои","2ms":"твои","2fs":"твои","3ms":"их","3fs":"их","1p":"наши","2mp":"ваши","2fp":"ваши","3mp":"их","3fp":"их"}
      },
      uk: {
        m: {"1s":"мій","2ms":"твій","2fs":"твій","3ms":"його","3fs":"її","1p":"наш","2mp":"ваш","2fp":"ваш","3mp":"їх","3fp":"їх"},
        f: {"1s":"моя","2ms":"твоя","2fs":"твоя","3ms":"його","3fs":"її","1p":"наша","2mp":"ваша","2fp":"ваша","3mp":"їх","3fp":"їх"},
        n: {"1s":"моє","2ms":"твоє","2fs":"твоє","3ms":"його","3fs":"її","1p":"наше","2mp":"ваше","2fp":"ваше","3mp":"їх","3fp":"їх"},
        pl:{"1s":"мої","2ms":"твої","2fs":"твої","3ms":"їх","3fs":"їх","1p":"наші","2mp":"ваші","2fp":"ваші","3mp":"їх","3fp":"їх"}
      },
      en: {
        any:{"1s":"my","2ms":"your","2fs":"your","3ms":"his","3fs":"her","1p":"our","2mp":"your","2fp":"your","3mp":"their","3fp":"their"}
      }
    };
    return map[lang]?.[nounGender]?.[person] || map[lang]?.any?.[person] || "";
  }

  function getCasePronoun(person, lang, selector) {
    const maps = {
      ru: {
        acc: {"1s":"меня","2ms":"тебя","2fs":"тебя","3ms":"его","3fs":"её","1p":"нас","2mp":"вас","2fp":"вас","3mp":"их","3fp":"их"},
        dat: {"1s":"мне","2ms":"тебе","2fs":"тебе","3ms":"ему","3fs":"ей","1p":"нам","2mp":"вам","2fp":"вам","3mp":"им","3fp":"им"},
        ins: {"1s":"мной","2ms":"тобой","2fs":"тобой","3ms":"им","3fs":"ею","1p":"нами","2mp":"вами","2fp":"вами","3mp":"ими","3fp":"ими"}
      },
      uk: {
        acc: {"1s":"мене","2ms":"тебе","2fs":"тебе","3ms":"його","3fs":"її","1p":"нас","2mp":"вас","2fp":"вас","3mp":"їх","3fp":"їх"},
        dat: {"1s":"мені","2ms":"тобі","2fs":"тобі","3ms":"йому","3fs":"їй","1p":"нам","2mp":"вам","2fp":"вам","3mp":"їм","3fp":"їм"},
        ins: {"1s":"мною","2ms":"тобою","2fs":"тобою","3ms":"ним","3fs":"нею","1p":"нами","2mp":"вами","2fp":"вами","3mp":"ними","3fp":"ними"}
      },
      en: {
        acc: {"1s":"me","2ms":"you","2fs":"you","3ms":"him","3fs":"her","1p":"us","2mp":"you","2fp":"you","3mp":"them","3fp":"them"},
        dat: {"1s":"me","2ms":"you","2fs":"you","3ms":"him","3fs":"her","1p":"us","2mp":"you","2fp":"you","3mp":"them","3fp":"them"},
        ins: {"1s":"me","2ms":"you","2fs":"you","3ms":"him","3fs":"her","1p":"us","2mp":"you","2fp":"you","3mp":"them","3fp":"them"}
      }
    };
    return maps[lang]?.[selector]?.[person] || "";
  }

  function buildTranslation(baseWord, person, lang, manualSelector = "") {
    if (!baseWord) return "";
    if (["acc","dat","ins"].includes(manualSelector)) {
      const pron = getCasePronoun(person, lang, manualSelector);
      if (!pron) return baseWord;
      return `${baseWord} ${pron}`.trim();
    }
    const nounGender = inferNounGender(baseWord, lang);
    const pron = getPossessivePronoun(person, lang, nounGender);
    if (!pron) return baseWord;
    return `${pron} ${baseWord}`;
  }

  function findAnalogForm(entry, person) {
    const forms = getFormsWithPersons(entry);
    return forms.find((f) => f.person === person) || null;
  }


function buildFormsFromAnalog(baseHe, analogEntry) {
  if (!analogEntry?.base?.he || !Array.isArray(analogEntry.forms)) return null;

  const srcBaseRaw = normalizeSpaces(analogEntry.base.he);
  const dstBaseRaw = normalizeSpaces(baseHe);

  const srcBaseNoNiq = stripNiqqud(srcBaseRaw);
  const dstBaseNoNiq = stripNiqqud(dstBaseRaw);

  if (!srcBaseNoNiq || !dstBaseNoNiq) return null;

  const result = [];

  for (const person of PERSON_ORDER) {
    const srcForm = findAnalogForm(analogEntry, person);
    if (!srcForm?.form) return null;

    const srcFormRaw = normalizeSpaces(srcForm.form);
    const parts = splitAroundBaseWithNiqqud(srcFormRaw, srcBaseRaw);
    if (!parts) return null;

    const generatedRaw = parts.prefix + dstBaseRaw + parts.suffix;

    result.push({
      person,
      label: PERSON_LABELS[person] || person,
      form: generatedRaw
    });
  }

  return result;
}

  function buildGeneratedEntry(inputTerm, uiLang) {
    const lang = detectLanguage(inputTerm);
    const analog = findBestAnalog(inputTerm, lang);
    if (!analog?.entry) {
      return {
        needsReview: true,
        reason: lang === "he"
          ? "Нет полной модели 1:1 для генерации"
          : "Для ru/uk/en без готовой связки с ивритской основой генерация недоступна"
      };
    }

    const source = analog.entry;
    const sourceModel = source.model || inferModelFromHebrew(source?.base?.he || "");
    const strictReport = lang === "he" ? getStrictnessReport(inputTerm, source) : null;

    let base = {
      he: source?.base?.he || "",
      ru: source?.base?.ru || "",
      uk: source?.base?.uk || "",
      en: source?.base?.en || ""
    };

    const cleanInput = normalizeSpaces(inputTerm);

    if (lang === "he") base.he = cleanInput;
    if (lang === "ru") base.ru = cleanInput;
    if (lang === "uk") base.uk = cleanInput;
    if (lang === "en") base.en = cleanInput;

    if (!base.he) {
      return {
        needsReview: true,
        reason: "Нет ивритской основы для надёжного склонения",
        analog
      };
    }

    const formsHe = buildFormsFromAnalog(base.he, source);
    if (!formsHe) {
      return {
        needsReview: true,
        reason: "Не удалось построить формы по аналогу",
        analog
      };
    }

    const forms = formsHe.map((f) => ({
      person: f.person,
      label: f.label,
      form: f.form,
      tr: {
        ru: buildTranslation(base.ru, f.person, "ru", ""),
        uk: buildTranslation(base.uk || base.ru, f.person, "uk", ""),
        en: buildTranslation(base.en || base.ru, f.person, "en", "")
      },
      examples: {
        he: "",
        ru: "",
        uk: "",
        en: ""
      }
    }));

    return {
      type: source.type || "A",
      model: sourceModel || "unknown_model",
      generated: true,
      needsReview: false,
      sourceAnalogKey: analog.key,
      sourceAnalogHe: source?.base?.he || "",
      strictReport,
      base,
      aliases: {
        he: [],
        ru: [],
        uk: [],
        en: []
      },
      forms
    };
  }



  function hasNiqqud(s) {
    return /[֑-ׇ]/.test(String(s || ""));
  }

  function placeholderByLang(lang) {
    return "";
  }

  function buildTranslationOrPlaceholder(baseWord, person, lang, manualSelector = "") {
    if (!baseWord || baseWord === "—") return "";
    return buildTranslation(baseWord, person, lang, manualSelector) || "";
  }

  function rebuildFormTranslations(entry) {
    if (!entry || !Array.isArray(entry.forms)) return entry;
    const base = entry.base || {};
    const manualSelector = entry.manualSelector || "";
    entry.forms = entry.forms.map((f) => ({
      ...f,
      tr: {
        ru: buildTranslationOrPlaceholder(base.ru, f.person, "ru", manualSelector),
        uk: buildTranslationOrPlaceholder(base.uk || base.ru, f.person, "uk", manualSelector),
        en: buildTranslationOrPlaceholder(base.en || base.ru, f.person, "en", manualSelector)
      }
    }));
    return entry;
  }


  function generateSimpleNounForms(baseHe) {
    const word = normalizeSpaces(baseHe);
    if (!word) return null;

    const bare = stripNiqqud(word);

    if (hasNiqqud(word)) {
      return [
        { person: "1s",  label: PERSON_LABELS["1s"],  form: word + "ִי" },
        { person: "2ms", label: PERSON_LABELS["2ms"], form: word + "ְךָ" },
        { person: "2fs", label: PERSON_LABELS["2fs"], form: word + "ֵךְ" },
        { person: "3ms", label: PERSON_LABELS["3ms"], form: word + "וֹ" },
        { person: "3fs", label: PERSON_LABELS["3fs"], form: word + "ָהּ" },
        { person: "1p",  label: PERSON_LABELS["1p"],  form: word + "ֵנוּ" },
        { person: "2mp", label: PERSON_LABELS["2mp"], form: word + "ְכֶם" },
        { person: "2fp", label: PERSON_LABELS["2fp"], form: word + "ְכֶן" },
        { person: "3mp", label: PERSON_LABELS["3mp"], form: word + "ָם" },
        { person: "3fp", label: PERSON_LABELS["3fp"], form: word + "ָן" }
      ];
    }

    const stem = bare.replace(/י$/, "");
    return [
      { person: "1s",  label: PERSON_LABELS["1s"],  form: stem + "ִי" },
      { person: "2ms", label: PERSON_LABELS["2ms"], form: stem + "ְךָ" },
      { person: "2fs", label: PERSON_LABELS["2fs"], form: stem + "ֵךְ" },
      { person: "3ms", label: PERSON_LABELS["3ms"], form: stem + "וֹ" },
      { person: "3fs", label: PERSON_LABELS["3fs"], form: stem + "ָהּ" },
      { person: "1p",  label: PERSON_LABELS["1p"],  form: stem + "ֵנוּ" },
      { person: "2mp", label: PERSON_LABELS["2mp"], form: stem + "ְכֶם" },
      { person: "2fp", label: PERSON_LABELS["2fp"], form: stem + "ְכֶן" },
      { person: "3mp", label: PERSON_LABELS["3mp"], form: stem + "ָם" },
      { person: "3fp", label: PERSON_LABELS["3fp"], form: stem + "ָן" }
    ];
  }


  function createBaseWithManualHebrew(inputTerm, manualHebrew, uiLang) {
    const termLang = detectLanguage(inputTerm);
    const cleanInput = normalizeSpaces(inputTerm);
    const cleanHeb = normalizeSpaces(manualHebrew);

    const base = {
      he: cleanHeb,
      ru: "",
      uk: "",
      en: ""
    };

    const targetLang = (termLang === "ru" || termLang === "uk" || termLang === "en")
      ? termLang
      : (uiLang === "ru" || uiLang === "uk" || uiLang === "en" ? uiLang : "ru");

    if (cleanInput && targetLang !== "he") {
      base[targetLang] = cleanInput;
    }

    return base;
  }

  function buildGeneratedNounEntryFromBase(base) {
    if (!base || !base.he) {
      return {
        needsReview: true,
        reason: "Для генерации нужна ивритская основа"
      };
    }

    const formsHe = generateSimpleNounForms(base.he);
    if (!formsHe) return null;

    return {
      type: "B",
      model: "simple_noun_like",
      generated: true,
      needsReview: false,
      sourceAnalogKey: "",
      sourceAnalogHe: "",
      base,
      aliases: { he: [], ru: [], uk: [], en: [] },
      forms: formsHe.map((f) => ({
        person: f.person,
        label: f.label,
        form: f.form,
        tr: {
          ru: buildTranslationOrPlaceholder(base.ru, f.person, "ru", ""),
          uk: buildTranslationOrPlaceholder(base.uk || base.ru, f.person, "uk", ""),
          en: buildTranslationOrPlaceholder(base.en || base.ru, f.person, "en", "")
        },
        examples: { he: "", ru: "", uk: "", en: "" }
      }))
    };
  }

  function createFromManualBase(inputTerm, manualHebrew, uiLang = "ru", manualSelector = "") {
    loadTABLES2FromStorage();
    mergeGeneratedIntoTables();

    const cleanInput = normalizeSpaces(inputTerm);
    const cleanHeb = normalizeSpaces(manualHebrew);

    if (!cleanInput) {
      return { status: "not_found", error: "Введите слово." };
    }
    if (!cleanHeb) {
      return { status: "needs_review", reason: "Введите перевод на иврите." };
    }
    if (typeof autoDetectNotDeclinable === "function" && autoDetectNotDeclinable(cleanInput, cleanHeb)) {
      return { status: "not_declinable", error: "Предлог или слово не склоняется в иврите при помощи местоименных суффиксов" };
    }

    const existingByInput = findEntryInTablesOnly(cleanInput) || findEntryInGeneratedOnly(cleanInput);
    if (existingByInput) {
      return { status: "found", ...existingByInput };
    }
    if (findEntryInTables2Only(cleanInput) || autoDetectNotDeclinable(cleanInput, cleanHeb)) {
      return { status: "not_declinable", error: "Предлог или слово не склоняется в иврите при помощи местоименных суффиксов" };
    }

    const existingByHeb = findEntryInTablesOnly(cleanHeb) || findEntryInGeneratedOnly(cleanHeb);
    if (existingByHeb && existingByHeb.entry) {
      const entry = clone(existingByHeb.entry);
      entry.base = entry.base || { he: cleanHeb, ru: "", uk: "", en: "" };
      const termLang = detectLanguage(cleanInput);
      const targetLang = (termLang === "ru" || termLang === "uk" || termLang === "en")
        ? termLang
        : (uiLang === "ru" || uiLang === "uk" || uiLang === "en" ? uiLang : "ru");
      entry.base.he = cleanHeb || entry.base.he || "";
      if (targetLang !== "he") {
        entry.base[targetLang] = cleanInput;
      }
      if (targetLang === "ru") {
        entry.base.uk = entry.base.uk || cleanInput;
        entry.base.en = entry.base.en || cleanInput;
      }
      entry.aliases = entry.aliases || { he: [], ru: [], uk: [], en: [] };
      entry.aliases[targetLang] = Array.isArray(entry.aliases[targetLang]) ? entry.aliases[targetLang] : [];
      if (cleanInput && !entry.aliases[targetLang].includes(cleanInput)) {
        entry.aliases[targetLang].push(cleanInput);
      }

      entry.manualSelector = manualSelector || "";
      rebuildFormTranslations(entry);
      const saved = saveGeneratedEntry(entry);
      return { status: "generated", key: saved.key, entry: saved.entry };
    }

    let generated = buildGeneratedEntry(cleanHeb, uiLang);
    if (generated) {
      generated.base = Object.assign({}, generated.base || {}, createBaseWithManualHebrew(cleanInput, cleanHeb, uiLang));
      generated.manualSelector = manualSelector || "";
      rebuildFormTranslations(generated);
    }

    if (!generated || generated.needsReview) {
      generated = buildGeneratedNounEntryFromBase(createBaseWithManualHebrew(cleanInput, cleanHeb, uiLang));
      if (generated) generated.manualSelector = manualSelector || "";
    }

    if (!generated) {
      return { status: "not_found", error: "Не удалось подобрать модель склонения" };
    }

    rebuildFormTranslations(generated);
    const saved = saveGeneratedEntry(generated);
    return { status: "generated", key: saved.key, entry: saved.entry };
  }

  function buildGeneratedNounEntry(inputTerm, uiLang) {
    const lang = detectLanguage(inputTerm);
    const cleanInput = normalizeSpaces(inputTerm);

    let base = {
      he: "",
      ru: placeholderByLang("ru"),
      uk: placeholderByLang("uk"),
      en: placeholderByLang("en")
    };

    if (lang === "he") base.he = cleanInput;
    if (lang === "ru") base.ru = cleanInput;
    if (lang === "uk") base.uk = cleanInput;
    if (lang === "en") base.en = cleanInput;

    if (!base.he) {
      return {
        needsReview: true,
        reason: "Для генерации нужна ивритская основа"
      };
    }

    const formsHe = generateSimpleNounForms(base.he);
    if (!formsHe) return null;

    return {
      type: "B",
      model: "simple_noun_like",
      generated: true,
      needsReview: false,
      sourceAnalogKey: "",
      sourceAnalogHe: "",
      base,
      aliases: { he: [], ru: [], uk: [], en: [] },
      forms: formsHe.map((f) => ({
        person: f.person,
        label: f.label,
        form: f.form,
        tr: {
          ru: buildTranslationOrPlaceholder(base.ru, f.person, "ru", ""),
          uk: buildTranslationOrPlaceholder(base.uk || base.ru, f.person, "uk", ""),
          en: buildTranslationOrPlaceholder(base.en || base.ru, f.person, "en", "")
        },
        examples: { he: "", ru: "", uk: "", en: "" }
      }))
    };
  }

  function saveGeneratedEntry(entry) {
    ensureGlobals();

    const keyBase =
      entry?.base?.he ||
      entry?.base?.ru ||
      entry?.base?.uk ||
      entry?.base?.en ||
      ("generated_" + Date.now());

    let key = makeSafeKey(keyBase);

    if (window.TABLES[key] || window.TABLES3[key]) {
      key += "_" + Date.now();
    }

    window.TABLES3[key] = Object.assign(clone(entry), { source: "generated", status: "draft" });
    saveTABLES2ToStorage();
    mergeGeneratedIntoTables();

    return { key, entry: window.TABLES3[key] };
  }

  function exportTABLES2AsJs() {
    return "window.TABLES2 = " + JSON.stringify(window.TABLES3 || {}, null, 2) + ";";
  }

  function findOrGenerate(term, uiLang = "ru") {
    loadTABLES2FromStorage();
    mergeGeneratedIntoTables();

    const foundInTables = findEntryInTablesOnly(term);
    if (foundInTables) return { status: "found", ...foundInTables };

    const foundInGenerated = findEntryInGeneratedOnly(term);
    if (foundInGenerated) return { status: "found", ...foundInGenerated };

    if (findEntryInTables2Only(term) || (typeof autoDetectNotDeclinable === "function" && autoDetectNotDeclinable(term, term))) {
      return {
        status: "not_declinable",
        error: "Предлог или слово не склоняется в иврите при помощи местоименных суффиксов"
      };
    }

    let generated = buildGeneratedEntry(term, uiLang);
    if (!generated) generated = buildGeneratedNounEntry(term, uiLang);

    if (!generated) {
      return {
        status: "not_found",
        error: "Не удалось подобрать модель склонения"
      };
    }

    if (generated.needsReview) return { status: "needs_review", ...generated };

    rebuildFormTranslations(generated);
    const saved = saveGeneratedEntry(generated);
    return { status: "generated", key: saved.key, entry: saved.entry, source: "tables3" };
  }

  function getEntryByKey(key) {
    const all = getAllTablesMerged();
    return all[key] || null;
  }

  function listGeneratedEntries() {
    loadTABLES2FromStorage();
    return clone(window.TABLES3 || {});
  }

  function deleteGeneratedEntry(key) {
    ensureGlobals();

    if (!window.TABLES3[key]) return false;

    delete window.TABLES3[key];
    saveTABLES2ToStorage();

    return true;
  }

  function clearGeneratedEntries() {
    ensureGlobals();
    window.TABLES3 = {};
    saveTABLES2ToStorage();
  }

  function initGenerator() {
    ensureGlobals();
    loadTABLES2FromStorage();
    mergeGeneratedIntoTables();
    console.log("Generator clean-translation initialized");
  }

  window.Generator = {
    init: initGenerator,
    findOrGenerate,
    findEntryEverywhere,
    findEntryInTablesOnly,
    findEntryInGeneratedOnly,
    findEntryInTables2Only,
    findBestAnalog,
    buildGeneratedEntry,
    createFromManualBase,
    listGeneratedEntries,
    deleteGeneratedEntry,
    clearGeneratedEntries,
    exportTABLES2AsJs,
    getEntryByKey,
    normalizeForCompare,
    stripNiqqud,
    inferModelFromHebrew,
    isLikelyIndeclinable,
    autoDetectNotDeclinable
  };

  initGenerator();
})();
