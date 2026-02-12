# SciPapers 子模块更新工作流程

## 目录结构

```
SciPapers (父仓库)
├── .gitmodules
├── academic-agent/    (子模块)
├── logseq-mcp/        (子模块)
├── feedder-mcp/       (子模块)
└── zotero-mcp/        (子模块)
```

## 工作流程

### 场景 1: 更新子模块的远程更改到本地

```bash
# 在 SciPapers 父仓库中
cd E:\Desktop\SciPapers

# 方法一：更新所有子模块到最新提交
git submodule update --remote --merge

# 方法二：更新特定子模块
git submodule update --remote logseq-mcp

# 方法三：更新并清理（推荐）
git submodule update --init --recursive --remote --merge
```

### 场景 2: 修改子模块并提交

```bash
# 1. 进入子模块目录
cd logseq-mcp

# 2. 进行修改（编辑代码）
# ...

# 3. 提交到子模块的远程仓库
git add .
git commit -m "feat: some feature"
git push origin main

# 4. 回到父仓库，记录子模块更新
cd ..

# 5. 在父仓库中提交子模块更新
git add logseq-mcp
git commit -m "chore: update logseq-mcp submodule"
git push origin main
```

### 场景 3: 修改 academic-agent 独立仓库

```bash
# 1. 进入 academic-agent 目录
cd academic-agent

# 2. 进行修改
# ...

# 3. 提交到 academic-agent 的远程仓库
git add .
git commit -m "feat: some feature"
git push origin main

# 4. 回到父仓库，记录更新
cd ..

# 5. 在父仓库中提交
git add academic-agent
git commit -m "chore: update academic-agent submodule"
git push origin main
```

### 场景 4: 克隆整个项目（新机器）

```bash
# 克隆父仓库
git clone https://github.com/liuchzzyy/SciPapers.git
cd SciPapers

# 初始化并更新所有子模块
git submodule update --init --recursive
```

### 场景 5: 日常开发完整流程

```bash
# 1. 拉取父仓库最新更改
git pull origin main

# 2. 更新所有子模块
git submodule update --init --recursive --remote --merge

# 3. 如果需要修改某个子模块
cd logseq-mcp
git pull origin main
# ... 进行修改 ...
git add .
git commit -m "feat: add feature"
git push origin main

# 4. 回到父仓库提交子模块更新
cd ..
git add logseq-mcp
git commit -m "chore: update logseq-mcp to latest"
git push origin main
```

## 常用命令

### 查看子模块状态
```bash
git submodule status
```

### 同步子模块 URL（如果 .gitmodules 改变了）
```bash
git submodule sync
```

### 仅初始化新添加的子模块
```bash
git submodule update --init
```

### 检出子模块的特定提交
```bash
cd logseq-mcp
git checkout <commit-hash>
cd ..
git add logseq-mcp
git commit -m "chore: pin logseq-mcp to specific commit"
```

### 删除子模块（如果需要）
```bash
# 1. 反初始化子模块
git submodule deinit -f logseq-mcp

# 2. 删除 .git/modules 中的数据
git rm -f logseq-mcp

# 3. 从 .gitmodules 中删除相应行
# 手动编辑 .gitmodules

# 4. 提交
git add .gitmodules
git commit -m "chore: remove logseq-mcp submodule"
```

## 注意事项

1. **子模块是独立的 Git 仓库**：每个子模块都有自己的提交历史
2. **父仓库只记录子模块的 commit SHA**：父仓库不存储子模块的文件内容，只存储指向特定提交的指针
3. **推送顺序很重要**：先推送子模块的更改，再推送父仓库的更改
4. **拉取时**：先拉取父仓库，再更新子模块
5. **避免在子模块目录中直接操作父仓库**

## 快速参考

| 操作 | 命令 |
|------|------|
| 初始化所有子模块 | `git submodule update --init --recursive` |
| 更新所有子模块 | `git submodule update --remote --merge` |
| 查看子模块状态 | `git submodule status` |
| 进入子模块 | `cd logseq-mcp` |
| 返回父仓库 | `cd ..` |
| 提交子模块更改 | 在子模块内 `git push`，然后在父仓库 `git add <submodule> && git commit` |
