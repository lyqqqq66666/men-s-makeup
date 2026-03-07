# 智颜方正 - 登录与注册页面 UI 重设计提示词 (Prompts)

## 🎨 整体设计风格与主题调性 (Design Style & Theme)
考虑到系统是“智能图像矫正与风格男妆生成”，设计应兼具**科技感 (AI计算)**与**美学感 (美妆/影像)**。
- **视觉风格**: 毛玻璃效果 (Glassmorphism)、明亮浅色主题 (Light Mode) 或极简纯净的白色/浅灰色背景。
- **色彩搭配**: 以浅色背景为主（如珍珠白、浅灰），文字保持高对比度深色，搭配柔和充满活力的渐变强调色（如晨颜粉、赛博蓝等），保留极简与优雅的高级感。
- **排版质感**: 现代无衬线字体，大留白，边缘处理圆润，交互带有平滑的微动效。

---

## 🔑 场景一：登录面板 (Login Panel Redesign)

**中文提示词 (用于规划或沟通)**:
> 帮我设计一个高端、现代的 Web 端登录界面，适用于一款名为“智颜方正”的 AI 智能图像处理系统。
> 1. **背景**: 采用明亮、清新的浅色背景，带有轻微的透气感或极淡的几何光晕，营造既专业又亲切的智能美妆氛围。
> 2. **主体布局**: 在屏幕中央（或右侧）悬浮一个高亮度的半透明毛玻璃质感 (Glassmorphism) 登录卡片。卡片内文字颜色须采用深灰或纯黑以保证清晰度。
> 3. **头部信息**: 顶部放置优雅的品牌主标题“欢迎回来，探索智颜”，副标题“登录以继续您的专属形象塑造”。
> 4. **输入框**: 包含“手机号”和“密码”。输入框采用无边框或底部高光边框设计，获得焦点时边框会有平滑的色彩渐变过渡，内部带极简图标。
> 5. **核心操作**: 一个具有视觉冲击力的“登录”主按钮，背景采用流光渐变色，hover悬浮时按钮带有发光扩散效果。
> 6. **辅助操作**: 清晰且不喧宾夺主的“忘记密码？”和“还没有账号？立即注册”链接。
> 7. **第三方登录**: 底部放置一组极简线框风格的快捷登录图标，必须包含“微信 (WeChat)”与“Google”图标。

**英文提示词 (更适合 v0.dev / ChatGPT 等 AI 代码生成工具)**:
> Design a premium, modern web login interface for an AI-powered smart image correction and male makeup generation system named "ZhiYan".
> 1. **Background**: Light, clean and fresh background with subtle and soft glowing effects, creating a professional and approachable tech-beauty atmosphere.
> 2. **Layout**: A floating light-themed glassmorphism translucent login card centered on the screen. The text inside should be dark gray or black for strong contrast.
> 3. **Header**: Elegant main title saying "Welcome Back", with a minimal dark subtitle "Log in to continue your personal styling."
> 4. **Inputs**: Mobile Phone Number and Password fields with modern, clean, light-colored backgrounds and dark texts. Include smooth color transitions on border focus, and minimalist icons inside.
> 5. **Primary Button**: A striking "Login" button with a sleek modern gradient and a subtle sleek shadow or hover effect, indicating AI power.
> 6. **Secondary Links**: "Forgot password?" and "Don't have an account? Sign up" text elements nicely aligned in dark color.
> 7. **Social Login**: Minimalist outline icons including "WeChat" and "Google" for quick social media login at the bottom.

---

## 📝 场景二：注册面板 (Registration Panel Redesign)

注册页面的提示词严格保持与登录页的**主题一致性**，只在内容表单上进行扩充。

**中文提示词**:
> 基于上述登录页面的“浅色清新主题与毛玻璃质感”，设计对应的用户注册界面。
> 1. **卡片视觉**: 保持完全一致的毛玻璃悬浮卡片设计，让用户从登录切换到注册时有完美的视觉连贯性。
> 2. **头部信息**: 标题改为“开启智颜之旅”，副标题为“加入我们，体验前沿的 AI 男妆生成与图像修正”。
> 3. **输入表单**: 包含以下输入栏，要求排版紧凑不拥挤：
>    - 手机号
>    - 密码
>    - 验证码 (输入框右侧内嵌一个“获取验证码”的幽灵按钮)
> 4. **细节设计**: 在密码框下方增加一个科技感十足的“密码强度指示条”（红/黄/绿渐变显示强度）。
> 5. **核心操作**: 突出的“立即注册”渐变色主按钮，样式与登录按钮一致。
> 6. **用户协议**: 按钮上方放置一个小巧的自定义复选框，文本为“我已阅读并同意《用户协议》和《隐私政策》”，协议文字高亮。
> 7. **底部引导**: “已有账号？返回登录”的友好文字引导链接。

**英文提示词 (针对 AI 代码生成工具)**:
> Based strictly on the design language, light mode, and glassmorphism theme of the previous login page, design the corresponding user registration interface.
> 1. **Consistency**: Maintain the exact same light-themed floating glassmorphic card design and fresh background for perfect visual continuity (use dark text for readability).
> 2. **Header**: Title "Start Your Journey", with dark subtitle "Join us to experience cutting-edge AI male makeup and image correction."
> 3. **Form Fields**: Cleanly organized and well-spaced input fields (light backgrounds, dark texts) for:
>    - Mobile Phone Number
>    - Password
>    - Verification Code (with an inline "Get Code" ghost button inside the input field)
> 4. **UI Details**: Add a sleek, modern "Password Strength Indicator" bar right below the password field.
> 5. **Primary Button**: A prominent "Sign Up" gradient button matching the exact style and hover effects of the login button.
> 6. **Terms**: A custom styled checkbox with dark text "I have read and agree to the Terms of Service and Privacy Policy" placed above the main button.
> 7. **Footer**: A clean dark text link "Already have an account? Log in."
