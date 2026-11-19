/* Shared storage for user-created Hebrew conjugations and their examples.
   Never reset or erase saved data on page load. */
(function () {
  'use strict';
  var CONJ = 'hebrewVerbsLocalRecords';
  var EXAMPLES = 'hebrewVerbIndependentExamplesV1';

  function norm(value) {
    return String(value == null ? '' : value).normalize('NFKC').toLowerCase()
      .replace(/[\u0591-\u05c7]/g, '').replace(/\s+/g, ' ').trim();
  }
  function read(key) {
    try { var value = JSON.parse(localStorage.getItem(key) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch (error) { console.error('Cannot read verb storage:', key, error); return {}; }
  }
  function write(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
  function aliases(record, key) {
    var inf = record && record.data && record.data.infinitive || {};
    return [key, record && record.base, inf.he, inf.ru, inf.uk, inf.en]
      .concat(record && Array.isArray(record.aliases) ? record.aliases : [])
      .map(norm).filter(Boolean);
  }
  function removeVerb(query) {
    var conjugations = read(CONJ), examples = read(EXAMPLES), target = norm(query);
    if (!target) return { removed: 0, examplesRemoved: 0 };
    var keys = Object.keys(conjugations).filter(function (key) {
      return aliases(conjugations[key], key).indexOf(target) !== -1;
    });
    if (!keys.length) return { removed: 0, examplesRemoved: 0 };
    // Delete all entries for the same Hebrew infinitive, even if stored under aliases.
    var hebrew = keys.map(function (key) {
      return norm(conjugations[key] && conjugations[key].data && conjugations[key].data.infinitive && conjugations[key].data.infinitive.he);
    }).filter(Boolean);
    keys = Object.keys(conjugations).filter(function (key) {
      var inf = conjugations[key] && conjugations[key].data && conjugations[key].data.infinitive;
      return keys.indexOf(key) !== -1 || (inf && hebrew.indexOf(norm(inf.he)) !== -1);
    });
    var deleted = keys.map(function (key) { return { key: key, record: conjugations[key] }; });
    var allAliases = new Set();
    deleted.forEach(function (item) { aliases(item.record, item.key).forEach(function (alias) { allAliases.add(alias); }); });
    keys.forEach(function (key) { delete conjugations[key]; });
    // Do not erase examples that are also referenced by another saved verb.
    Object.keys(conjugations).forEach(function (key) {
      aliases(conjugations[key], key).forEach(function (alias) { allAliases.delete(alias); });
    });
    var examplesRemoved = 0;
    Object.keys(examples).forEach(function (key) {
      if (allAliases.has(norm(key))) { delete examples[key]; examplesRemoved++; }
    });
    // Commit examples first, then conjugations; on failure try to restore examples.
    var oldExamples = read(EXAMPLES);
    try {
      write(EXAMPLES, examples);
      try { write(CONJ, conjugations); }
      catch (error) { write(EXAMPLES, oldExamples); throw error; }
    } catch (error) { console.error('Unable to delete saved verb:', error); throw error; }
    // Remove only the in-memory objects loaded from these user records.
    // Never delete a manually authored verbsDB entry merely by matching its name.
    if (window.verbsDB) {
      Object.keys(window.verbsDB).forEach(function (key) {
        if (deleted.some(function (item) { return item.record && window.verbsDB[key] === item.record.data; })) {
          delete window.verbsDB[key];
        }
      });
    }
    if (window.__currentSavedConjugation &&
        deleted.some(function (item) { return window.__currentSavedConjugation.base === item.key; })) {
      window.__currentSavedConjugation = null;
    }
    window.dispatchEvent(new CustomEvent('hebrew-verb-storage-deleted', {
      detail: { keys: keys, hebrew: hebrew, examplesRemoved: examplesRemoved }
    }));
    return { removed: keys.length, examplesRemoved: examplesRemoved, keys: keys };
  }
  function saveExamples(record, rows, query) {
    if (!record || !record.data || !record.data.infinitive || !Array.isArray(rows) || !rows.length)
      throw new Error('A saved verb and examples are required');
    var stored = read(EXAMPLES);
    aliases(record, record.base).concat([norm(query)]).filter(Boolean).forEach(function (key) {
      stored[key] = rows;
    });
    write(EXAMPLES, stored);
    return true;
  }
  window.verbStorage = Object.freeze({
    conjugations: function () { return read(CONJ); },
    examples: function () { return read(EXAMPLES); },
    saveExamples: saveExamples,
    removeVerb: removeVerb,
    normalize: norm
  });
})();
