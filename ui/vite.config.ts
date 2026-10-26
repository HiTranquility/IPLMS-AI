/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// Hỗ trợ cả root / và các nested routes (/vision/label, /vision/review, /console/*) của `app.console_main`.
export default defineConfig({
  base: '/',
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    host: '127.0.0.1',
    port: 5190,
    strictPort: true,
    proxy: {
      '/console/api': 'http://127.0.0.1:8090',
      '/api': 'http://127.0.0.1:8090',
    },
  },
  build: { outDir: 'dist', assetsInlineLimit: 0, sourcemap: false },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: { modules: { classNameStrategy: 'non-scoped' } },
    maxWorkers: 2,
    fileParallelism: false,
    execArgv: [
      '--import',
      'data:text/javascript,import zlib from "node:zlib"; if (!zlib.createZstdDecompress) zlib.createZstdDecompress = zlib.createInflate;',
    ],
  },
});
