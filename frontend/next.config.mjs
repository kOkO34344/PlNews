/** @type {import('next').NextConfig} */
export default {
  // Deliberately no `env` block: keys listed there are inlined at build time, so a build
  // that ran without API_BASE bakes in the fallback and the page quietly serves sample
  // data. lib/api.ts is server-only, so process.env is read per request instead.
};
