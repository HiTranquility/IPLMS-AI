/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// Console chạy dưới /console/ của process `app.console_main` (ADR-0048); dev server
// chuyển /console/api sang process đó để cookie phiên giữ cùng nguồn.
export default defineConfig({
  base: '/console/',
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    host: '127.0.0.1',
    port: 5190,
    strictPort: true,
    proxy: { '/console/api': 'http://127.0.0.1:8090' },
  },
  build: { outDir: 'dist', assetsInlineLimit: 0, sourcemap: false },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: { modules: { classNameStrategy: 'non-scoped' } } },
});
