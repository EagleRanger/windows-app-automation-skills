'use strict';

// Thin helpers for the documented managed-tab browser runtime.
// The caller supplies the runtime object; this file has no credentials,
// no CDP/HTTP server, and no automatic login logic.

function expectedRegExp(expected) {
  if (expected instanceof RegExp) return expected;
  return new RegExp(String(expected).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
}

async function ensureTab(cua, options = {}) {
  if (!cua) throw Error('A browser automation runtime object is required');
  if (options.mention) return cua.getTab({ mention: options.mention });
  if (options.tabId) {
    const extra = options.browser ? { browser: options.browser } : {};
    return cua.getTab(options.tabId, extra);
  }
  if (options.browser && options.url) {
    const visible = options.visible !== false;
    return cua.createBrowserTab(options.browser, options.url, { visible });
  }
  throw Error('Provide mention, tabId, or browser+url; do not select an arbitrary tab');
}

async function describeTab(tab) {
  if (!tab) throw Error('A managed tab is required');
  const state = { url: await tab.url() };
  if (typeof tab.title === 'function') state.title = await tab.title();
  else if (tab.title) state.title = tab.title;
  return state;
}

async function assertPage(tab, expected) {
  const state = await describeTab(tab);
  const pattern = expectedRegExp(expected);
  if (!pattern.test(state.url)) {
    throw Error(`Unexpected page: ${state.url}; expected /${pattern.source}/`);
  }
  await tab.playwright.domSnapshot();
  return state;
}

async function safeClick(tab, locator, label = 'target') {
  const count = await locator.count();
  if (count !== 1) throw Error(`${label} locator matched ${count} elements, expected exactly 1`);
  if (!await locator.isVisible()) throw Error(`${label} is not visible`);
  await locator.click();
  const snapshot = await tab.playwright.domSnapshot();
  return { clicked: label, snapshot };
}

export { ensureTab, describeTab, assertPage, safeClick };
