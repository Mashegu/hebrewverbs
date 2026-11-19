/* Shared storage for user-created Hebrew conjugations and their examples.
   Existing saved records are preserved. */
(function () {
  'use strict';
  var CONJ = 'hebrewVerbsLocalRecords';
  var EXAMPLES = 'hebrewVerbIndependentExamplesV1';
  // Existing local records must never be reset automatically.
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
     if (!target) return { removed: 0, examplesRemoved: 0, keys: [] };
     // A key passed from the personal list must identify that exact record.
     // Only fall back to aliases for search-based deletion.
     var keys = Object.prototype.hasOwnProperty.call(conjugations, query)
       ? [query] : Object.keys(conjugations).filter(function (key) {
           var rec = conjugations[key], inf = rec && rec.data && rec.data.infinitive;
           return inf && norm(inf.he) === target;
         });
     if (!keys.length) {
       keys = Object.keys(conjugations).filter(function (key) {
         return aliases(conjugations[key], key).indexOf(target) !== -1;
       });
       // Ambiguous translations must not delete multiple unrelated verbs.
       var distinct = new Set(keys.map(function (key) {
         var inf = conjugations[key] && conjugations[key].data && conjugations[key].data.infinitive;
         return norm(inf && inf.he) || key;
       }));
       if (distinct.size > 1) return { removed: 0, examplesRemoved: 0, keys: [], ambiguous: true };
     }
     if (!keys.length) return { removed: 0, examplesRemoved: 0, keys: [] };
     var hebrew = keys.map(function (key) {
       var inf = conjugations[key] && conjugations[key].data && conjugations[key].data.infinitive;
       return norm(inf && inf.he);
     }).filter(Boolean);
     // Remove all duplicate saved records of this infinitive, but no other verb.
     keys = Object.keys(conjugations).filter(function (key) {
       var inf = conjugations[key] && conjugations[key].data && conjugations[key].data.infinitive;
       return keys.indexOf(key) !== -1 || (inf && hebrew.indexOf(norm(inf.he)) !== -1);
     });
     var deleted = keys.map(function (key) { return { key: key, record: conjugations[key] }; });
     var allAliases = new Set();
     deleted.forEach(function (item) { aliases(item.record, item.key).forEach(function (a) { allAliases.add(a); }); });
     keys.forEach(function (key) { delete conjugations[key]; });
     Object.keys(conjugations).forEach(function (key) {
       aliases(conjugations[key], key).forEach(function (a) { allAliases.delete(a); });
     });
     var examplesRemoved = 0;
     Object.keys(examples).forEach(function (key) {
       if (allAliases.has(norm(key))) { delete examples[key]; examplesRemoved++; }
     });
     var previousConjugations = localStorage.getItem(CONJ);
     var previousExamples = localStorage.getItem(EXAMPLES);
     try {
       write(CONJ, conjugations);
       write(EXAMPLES, examples);
     } catch (error) {
       try {
         if (previousConjugations === null) localStorage.removeItem(CONJ);
         else localStorage.setItem(CONJ, previousConjugations);
         if (previousExamples === null) localStorage.removeItem(EXAMPLES);
         else localStorage.setItem(EXAMPLES, previousExamples);
       } catch (restoreError) { console.error('Unable to restore saved verbs:', restoreError); }
       throw error;
     }
     if (window.verbsDB) Object.keys(window.verbsDB).forEach(function (key) {
       if (deleted.some(function (item) { return item.record && window.verbsDB[key] === item.record.data; })) delete window.verbsDB[key];
     });
     if (window.__currentSavedConjugation && deleted.some(function (item) {
       var current = window.__currentSavedConjugation;
       return current === item.record || norm(current.data && current.data.infinitive && current.data.infinitive.he) === norm(item.record && item.record.data && item.record.data.infinitive && item.record.data.infinitive.he);
     })) window.__currentSavedConjugation = null;
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
