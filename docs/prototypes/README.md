# HTML 原型说明

> **目的**：用 HTML 直接生成 PM 原型，替代 Figma 起步阶段的低效流程。
> **原则**：单文件、可在浏览器直接打开、与生产代码用同一套 Tailwind 样式。

## 文件清单

| 文件 | 页面 | 状态 |
|------|------|------|
| `login.html` | /login（登录/注册） | v1.0 |
| `chat.html` | /（聊天主页） | v1.0 |
| `quiz.html` | /quiz（随堂测试） | v1.0 |
| `vocabulary.html` | /vocabulary（词汇闪卡） | v1.0 |
| `progress.html` | /progress（学习进度） | v1.0 |

## 用法

### 1. 浏览器预览
```bash
# macOS
open docs/prototypes/login.html

# Linux
xdg-open docs/prototypes/login.html
```

### 2. 对比生产代码
- 原型用 Tailwind CDN（无构建步骤）
- 生产代码用 Tailwind PostCSS（构建后）
- 同样 utility class，迁移到生产时直接复制粘贴即可

### 3. 走查（Walkthrough）清单
- [ ] 注册 → 登录 流程
- [ ] 聊天 → 选模式 → 发消息 → 看到回复 + 模式标签 + 来源
- [ ] 出题 → 选单元/题型 → 答题 → 提交批改
- [ ] 词汇 → 翻面 → 标记认识/不认识
- [ ] 进度 → 看统计卡 + 薄弱单元 + 最近记录

### 4. 修改流程
- PM 改 HTML → 截图给团队 review → 验收后开发再写 React

## 与 Figma 的对比

| 维度 | HTML 原型 | Figma |
|------|----------|-------|
| 启动成本 | 0（浏览器即用） | 高（学软件） |
| 代码复用 | 100%（Tailwind 通用） | 0（需重写） |
| 真实数据 | 可以接 API | 仅静态 |
| 高保真度 | 中（够 PM 走查） | 极高（设计师/客户演示） |
| 协作评论 | 截图 | 内置 |
| **适用阶段** | **MVP / 内部走查** | **客户演示 / 营销** |

**结论**：MVP 阶段用 HTML，量大了再迁 Figma。
