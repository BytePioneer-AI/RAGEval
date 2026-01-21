# 仓库指南

## 项目结构与模块组织
- `src/` 存放 React + TypeScript 应用代码，按功能分层：`pages/`（页面）、`components/`（共享组件）、`router/`（路由）、`services/`（数据访问）、`hooks/`（自定义 Hooks）、`types/`（类型定义）。
- `public/` 存放直接对外的静态资源（logo、图片等）。
- `doc/` 存放产品与接口文档（中文）。
- `UI/` 存放静态 HTML 原型与参考页面。
- 根目录包含 `vite.config.ts`、TypeScript 配置文件与 `eslint.config.js`。

## 编码风格与命名规范
- 使用 TypeScript + 函数组件；路由由 React Router 管理。
- 缩进为 2 个空格；整理 import 分组，避免未使用导出。
- 组件文件使用 `PascalCase`（如 `MainLayout.tsx`），静态资源使用 `kebab-case`。
- 已配置 ESLint 与 Prettier；提交前运行 `npm run lint`。

## 提交与 PR 规范
- 近期提交消息多为简短命令式，如 `Update README.md` 或 `update`；建议沿用该风格，必要时可更具体。
- PR 需包含：简要说明、关联问题（如有）、UI 变更截图/GIF；如涉及配置或环境变量请注明。
