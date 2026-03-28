// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react()],
//   build: {
//     rollupOptions: {
//       output: {
//         manualChunks(id) {
//           // ① 把所有第三方库集中到 vendor.js
//           if (id.includes('node_modules')) return 'vendor'
//         }
//       }
//     },
//     brotliSize: true        // 只统计 brotli 体积，不会额外生成 .br 文件
//     },
//   server: {
//     allowedHosts: [
//       'newfrontend.ngrok.app',  // 把你的 ngrok 域名填在这里
//       'findpaper.cn',
//       'www.findpaper.cn'
//     ],
//     host: true,
//   }
// })


// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import compression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    react(),
    // ① 生成 .br 和 .gz 压缩文件
    compression({ algorithm: 'brotliCompress', ext: '.br', deleteOriginFile: false }),
    compression({ algorithm: 'gzip', ext: '.gz', deleteOriginFile: false }),
  ],
  build: {
    // 可选：把警告阈值调大一点，避免不必要提示
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // ② 把所有第三方库拆成 vendor.js，首页只加载你自己的代码
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        }
      }
    }
  },
  server: {
    // 这些和打包无关，保持就好
    allowedHosts: [
      'newfrontend.ngrok.app',
      'findpaper.cn',
      'www.findpaper.cn'
    ],
    host: true,
  }
})
