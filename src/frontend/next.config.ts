import type { NextConfig } from "next";

/** * 完整 Next.js 配置文件
 * 适用场景：AIO Sandbox 开发环境、解决跨域限制、忽略 TS 检查
 */
const nextConfig: NextConfig = {
  // 1. 【核心修正】开发环境安全源配置
  // 必须嵌套在 experimental 属性下，否则配置无效
  experimental: {
    // @ts-ignore
    allowedDevOrigins: [
      "*",                // 优先尝试通配符，允许所有外部 IP/域名访问开发服务器
      "localhost:3000",   // 本地回环
      "36.138.183.95",    // 你当前的公网 IP
      "36.138.183.95:3000"
    ],
  },

  // 2. 跨域 (CORS) 响应头配置
  // 解决浏览器 API 请求时的跨域拦截问题
  async headers() {
    return [
      {
        // 匹配所有路径
        source: '/:path*',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            // 允许所有来源，或使用 process.env.ALLOWED_ORIGIN
            value: '*', 
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'X-Requested-With, Content-Type, Authorization',
          },
          {
            key: 'Access-Control-Allow-Credentials',
            value: 'true',
          },
        ],
      },
      {
        // 特别处理 API 路由的跨域
        source: '/api/:path*',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'X-Requested-With, Content-Type, Authorization',
          },
        ],
      },
    ];
  },

  // 3. 代理配置 (Rewrites)
  async rewrites() {
    const backendPort = process.env.BACKEND_PORT || "30000";
    return [
      // 后端 API 代理
      {
        source: '/api/sandbox/:path*',
        destination: `http://localhost:${backendPort}/:path*`,
      },
      // Browser Service WebSocket 代理
      {
        source: '/ws/browser',
        destination: 'http://localhost:5690/ws/browser',
      },
      // 后端 WebSocket 代理 (保持现有逻辑)
      {
        source: '/ws/sandbox',
        destination: `http://localhost:${backendPort}/ws`,
      }
    ];
  },

  // 3. 部署与编译优化
  typescript: {
    // 在构建过程中忽略 TypeScript 错误，避免因类型问题导致部署失败
    ignoreBuildErrors: true, 
  },
  
  eslint: {
    // 构建时同样忽略 ESLint 检查（可选）
    ignoreDuringBuilds: true,
  },

  // 如果你需要使用 Docker 部署，建议开启此项
  // output: 'standalone', 
};

export default nextConfig;