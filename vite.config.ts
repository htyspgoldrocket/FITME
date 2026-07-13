import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// PWA 플러그인은 Phase 1-Step 4에서 설정한다 (규칙 4: Phase 범위 엄수)
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // 모바일 기기에서 같은 네트워크로 접속 가능하도록
  },
});
