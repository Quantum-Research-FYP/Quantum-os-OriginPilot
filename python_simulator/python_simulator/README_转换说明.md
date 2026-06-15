# 协议文档转换说明

## 已完成的工作

已成功将四个通信协议文档转换为LaTeX格式，并添加了目录：

### 生成的LaTeX文件：
1. `超导通信协议文档.tex` (31KB)
2. `光量子通信协议文档.tex` (29KB)
3. `离子阱通信协议文档.tex` (29KB)
4. `中性原子通信协议文档.tex` (29KB)

### LaTeX文件特性：
- ✅ 使用ctexart类支持中文
- ✅ 包含完整的目录（tableofcontents）
- ✅ 自动转换Markdown标题为LaTeX章节
- ✅ 转换表格为LaTeX longtable格式
- ✅ 转换列表为itemize环境
- ✅ 转换代码块为verbatim环境
- ✅ 转换粗体、斜体等格式
- ✅ 配置了超链接支持
- ✅ 优化了页面边距

## PDF编译说明

由于系统LaTeX环境缺少中文字体配置，PDF编译遇到问题。您可以选择以下任一方式编译：

### 方法1：安装中文字体后手动编译

```bash
# 进入目录
cd PilotPy/python_simulator

# 编译单个文档
pdflatex 超导通信协议文档.tex

# 或编译所有文档
for file in *.tex; do pdflatex "$file"; done
```

### 方法2：使用xelatex（推荐，如果已安装）

```bash
cd PilotPy/python_simulator
for file in *.tex; do xelatex "$file"; done
```

### 方法3：在线编译

您可以将.tex文件上传到在线LaTeX编辑器（如Overleaf）进行编译。

### 方法4：修复本地LaTeX字体

安装中文字体后，LaTeX文件应该可以正常编译：

```bash
# 在Debian/Ubuntu上
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei
sudo apt-get install texlive-lang-chinese
```

## 查看LaTeX文件

LaTeX文件是纯文本格式，可以直接用文本编辑器查看。您也可以在支持LaTeX的IDE（如TeXstudio、VS Code + LaTeX Workshop）中打开查看和编辑。

## 自定义编译

如果您想修改编译选项，可以编辑 `convert_to_latex.py` 脚本中的以下部分：

```python
# 修改字体集（如果使用xelatex）
\ctexset{fontset=ubuntu}  # 可选: ubuntu, windows, mac, adobe等

# 修改页面边距
\geometry{
    left=2.5cm,
    right=2.5cm,
    top=2.5cm,
    bottom=2.5cm
}
```

## 文件列表

```
PilotPy/python_simulator/
├── 超导通信协议文档.md      # 原始Markdown
├── 超导通信协议文档.tex      # 转换后的LaTeX（带目录）
├── 光量子通信协议文档.md
├── 光量子通信协议文档.tex
├── 离子阱通信协议文档.md
├── 离子阱通信协议文档.tex
├── 中性原子通信协议文档.md
├── 中性原子通信协议文档.tex
├── convert_to_latex.py        # 转换脚本
└── README_转换说明.md          # 本文件
```

## 转换脚本使用

如需重新转换或修改后重新生成：

```bash
python3 convert_to_latex.py
```

脚本会：
1. 读取所有四个Markdown文件
2. 转换为LaTeX格式
3. 添加目录
4. 尝试编译为PDF（如果字体配置正确）
5. 清理临时文件

## 问题排查

如果编译遇到字体问题，可以在.tex文件开头修改字体配置：

```latex
\documentclass{ctexart}
\ctexset{fontset=ubuntu}  % 修改为您的系统字体集
```

可选字体集：
- `ubuntu` - Ubuntu系统默认字体
- `windows` - Windows系统字体
- `mac` - macOS系统字体
- `adobe` - Adobe字体
- `fandol` - 方正字体
- `none` - 不使用字体集，手动指定
