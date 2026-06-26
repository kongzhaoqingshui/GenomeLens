# 在 Linux 下裸用 JCVI 复现 GenomeLens `synteny` 一键流程

> 本文用于课堂汇报：通过展示 Linux 下裸用 JCVI 所需的完整手动步骤，反衬 GenomeLens 在 Windows 本地"一条命令出结果"的集成价值。

## 1. 目标

复现 GenomeLens 这条命令在 Windows 上的效果：

```powershell
GenomeLens.exe analyze workflow synteny input output --force
```

该命令在 Windows 本地自动完成：

- 输入目录物种发现（BED/CDS 或 GFF/FASTA 自动识别）
- GFF 预处理为 BED/CDS
- 多物种自动拆分为 all-vs-all（或 reference-vs-targets）pairwise
- 每个 pairwise：BLAST+ 比对、锚点扫描、block 计算
- 自动出图：dotplot、synteny figure、karyotype
- 多物种时聚合为全局核型总图（global karyotype）
- 结果归档到统一目录结构

下面给出在 Linux 服务器上直接用上游 JCVI 完成相同任务的完整路径。

---

## 2. Linux 环境准备

### 2.1 基础依赖

```bash
# Ubuntu/Debian 示例
sudo apt-get update
sudo apt-get install -y build-essential wget curl git \
  python3-dev python3-pip python3-venv \
  libfreetype6-dev libpng-dev libjpeg-dev \
  texlive-latex-extra texlive-fonts-recommended dvipng

# 推荐用 conda 管理
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create -n jcvi python=3.12
conda activate jcvi
```

### 2.2 安装 JCVI 与 Python 绘图栈

```bash
conda activate jcvi
pip install jcvi matplotlib numpy pandas scipy biopython
```

> JCVI 官方依赖较多，安装时经常因 `pillow`、`matplotlib` 或 `texlive` 字体问题失败；Windows 用户无需关心这些，GenomeLens 已随包内置。

### 2.3 安装 BLAST+

```bash
# 下载 NCBI BLAST+ 并解压到 PATH
wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.16.0+-x64-linux.tar.gz
tar -xzf ncbi-blast-2.16.0+-x64-linux.tar.gz
export PATH=$PWD/ncbi-blast-2.16.0+/bin:$PATH
makeblastdb -version
```

> 若用 LAST 或 Diamond，还需单独下载、配置 PATH，并处理 JCVI 后端差异。GenomeLens Windows 版内置 BLAST+，且 `align_soft` 三后端在配置层统一。

---

## 3. 数据准备

GenomeLens 接受：

- `speciesA.bed` + `speciesA.cds`（或 `.pep`）
- 或 `speciesA.gff3` + `speciesA.fa`

JCVI 裸用需要先把 GFF 转成 BED/CDS：

```bash
python -m jcvi.formats.gff bed --type=gene --key=ID speciesA.gff3 -o speciesA.bed
python -m jcvi.formats.fasta format speciesA.fa speciesA.cds
```

> GenomeLens 自动完成 GFF→BED/CDS 转换，并统一不同注释来源的 ID 空间。

---

## 4. 双物种基础流程（最小复现）

假设已有 `query.bed/query.cds` 和 `subject.bed/subject.cds`。

### 4.1 建立 BLAST 数据库并比对

```bash
makeblastdb -in subject.cds -dbtype nucl -out subject.blastdb
blastn -query query.cds -db subject.blastdb -outfmt 6 \
  -evalue 1e-10 -num_threads 4 -out query.subject.blast.tsv
```

### 4.2 生成共线性锚点

```bash
python -m jcvi.compara.synteny.scan query.subject.blast.tsv query.bed subject.bed \
  -o query.subject.anchors
```

### 4.3 生成简化边文件

```bash
python -m jcvi.compara.synteny.simple query.subject.anchors query.bed subject.bed \
  -o query.subject.anchors.simple
```

### 4.4 计算共线性 blocks

```bash
python -m jcvi.compara.synteny.mcscan query.subject.anchors query.bed subject.bed \
  -s query.subject.anchors.simple -o query.subject.blocks
```

### 4.5 合并 BED（供后续绘图）

```bash
python -m jcvi.formats.bed.merge query.bed subject.bed -o all.bed
```

### 4.6 绘制点图

```bash
python -m jcvi.graphics.dotplot query.subject.anchors query.bed subject.bed --notex
```

### 4.7 绘制 synteny figure

需要手写 `synteny.layout`：

```text
# x, y, rotation, ha, va, color, ratio, label
0.5, 0.5, 0, center, center, g, 1, query
0.5, 0.7, 0, center, center, r, 1, subject
# edges
e, 0, 1
```

然后：

```bash
python -m jcvi.graphics.synteny query.subject.blocks all.bed synteny.layout \
  --notex --format svg -o synteny
```

### 4.8 绘制核型图

需要手写 `karyotype.seqids` 和 `karyotype.layout`：

```bash
cat > karyotype.seqids <<EOF
query_Chr1,query_Chr2,query_Chr3
subject_Chr1,subject_Chr2,subject_Chr3
EOF

python -m jcvi.graphics.karyotype karyotype.seqids karyotype.layout \
  --format svg --notex -o karyotype
```

> 手写 seqids/layout 是裸用 JCVI 最繁琐的环节之一；GenomeLens 根据输入自动推导默认 layout。

---

## 5. 多物种 all-vs-all 流程

 GenomeLens `synteny` 对 ≥3 个物种会自动拆成全部两两组合并汇总。裸用 JCVI 需要手动写循环：

```bash
mkdir -p pairwise
for sp1 in A B C; do
  for sp2 in A B C; do
    [ "$sp1" = "$sp2" ] && continue
    prefix="pairwise/${sp1}.${sp2}"
    makeblastdb -in ${sp2}.cds -dbtype nucl -out ${sp2}.blastdb
    blastn -query ${sp1}.cds -db ${sp2}.blastdb -outfmt 6 \
      -evalue 1e-10 -num_threads 4 -out ${prefix}.blast.tsv
    python -m jcvi.compara.synteny.scan ${prefix}.blast.tsv ${sp1}.bed ${sp2}.bed \
      -o ${prefix}.anchors
    python -m jcvi.compara.synteny.simple ${prefix}.anchors ${sp1}.bed ${sp2}.bed \
      -o ${prefix}.anchors.simple
    python -m jcvi.compara.synteny.mcscan ${prefix}.anchors ${sp1}.bed ${sp2}.bed \
      -s ${prefix}.anchors.simple -o ${prefix}.blocks
  done
done
```

### 5.1 聚合全局核型总图

需要把每个物种的 BED 整理成 tracks，把 `.simple` 文件整理成 edges，再手写全局 `seqids` 和 `layout`：

```bash
cat > tracks.txt <<EOF
A\tA.bed
B\tB.bed
C\tC.bed
EOF

cat > edges.txt <<EOF
0\t1\tpairwise/A.B.simple
0\t2\tpairwise/A.C.simple
1\t2\tpairwise/B.C.simple
EOF

# 需要自行计算每条染色体在图中的顺序、缩放比例、连线起止位置
python -m jcvi.graphics.karyotype global.seqids global.layout \
  --format svg --notex -o karyotype_global
```

> GenomeLens 自动完成 tracks/edges 组装、全局 layout 推导和总图渲染；裸用 JCVI 时这部分没有现成脚本，通常需要几百行 Python 胶水代码。

---

## 6. 局部共线性（target gene 模式）

GenomeLens 命令：

```powershell
GenomeLens.exe analyze workflow synteny input output `
  --reference query --target-genes AT1G01010 --up 20 --down 20 --force
```

裸用 JCVI 需要：

1. 先跑完对应 reference-vs-target 的 pairwise 得到 `.blocks`。
2. 根据参考物种 BED 顺序，找到目标基因上下游 20 个基因。
3. 从 `.blocks` 中筛选包含这些基因的局部 block。
4. 生成局部 `.local.blocks`、`.local.bed`、`.local.layout`。
5. 调用 `jcvi.graphics.synteny` 出图。

示例（仅示意，实际需要写 Python 脚本切窗口）：

```bash
python -m jcvi.graphics.synteny \
  AT1G01010.local.blocks all.local.bed AT1G01010.local.layout \
  --notex --format svg -o AT1G01010.local
```

> GenomeLens 自动完成目标基因定位、窗口截取、layout 生成和多目标分图。

---

## 7. 与 GenomeLens Windows 一键流程对比

| 步骤 | Linux 裸用 JCVI | GenomeLens on Windows |
|---|---|---|
| 环境安装 | conda、JCVI、BLAST+、LaTeX/字体逐个安装调试 | 下载即用，工具链随包/自动补全 |
| GFF 预处理 | 手动 `jcvi.formats.gff bed` + `jcvi.formats.fasta format` | 自动转换 |
| 物种发现 | 手动整理文件对 | 扫描目录自动识别 |
| 多物种拆分 | 手写 shell 循环 | 自动 all-vs-all |
| BLAST+ | 手动 `makeblastdb` / `blastn` | 自动调用，参数统一 |
| 锚点/block | 手动 scan / simple / mcscan | 自动串行 |
| 图件 | 手写 layout / seqids，逐个调用 dotplot/synteny/karyotype | 自动出图并归档 |
| 全局总图 | 手写 tracks/edges/global layout | 自动聚合 |
| 局部共线性 | 手写窗口截取脚本 | `--target-genes` 自动路由 |
| 结果结构 | 散落当前目录，需自行整理 | 统一 `report/`、`results/`、`intermediate/` |
| 命令行长度 | 数十条命令 + 多个手写配置文件 | 一条命令 |

---

## 8. 结论

裸用 JCVI 在 Linux 上当然可以完成同样的生物学分析，但它把大量工程细节暴露给了用户：

- 环境依赖管理
- BLAST+ 命令参数
- BED/CDS 格式转换与 ID 一致性
- layout / seqids 手写
- 多物种 pairwise 循环
- 全局总图聚合逻辑
- 局部共线性窗口截取
- 产物整理与归档

GenomeLens 在 Windows 本地把这些步骤封装为统一 CLI：

```powershell
GenomeLens.exe analyze workflow synteny input output --force
```

用户只需关心"输入目录"和"输出目录"，即可获得与裸用 JCVI 等价的标准图件和中间产物。这正是 GenomeLens 作为"Windows-first 本地比较基因组学平台"的核心价值：把 JCVI 的学术能力转化为可交付、可复现、低门槛的本地工具。

---

*本文档用于课堂汇报，展示 Linux 裸用路径的复杂性与 Windows 本地集成的便利性对比。*
