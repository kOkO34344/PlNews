/** @type {import('next').NextConfig} */
export default {
  env: { API_BASE: process.env.API_BASE ?? "http://localhost:8000/api" },
};
