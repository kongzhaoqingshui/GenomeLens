# JCVI 扩展功能集成建议

> 本文档梳理 JCVI 中除已集成工作流外、值得在 GenomeLens 中进一步封装的能力，按**集成难度**排序，并给出生物学意义、原始 Linux 命令与集成思路。
>
> 版本：基于当前 `genomelens` conda 环境中的 `jcvi` 包扫描结果。

---

## 1. 已集成的 JCVI 能力（参考基线）

| GenomeLens 工作流 | JCVI 原始入口 | 说明 |
|---|---|---|
| `graphics_synteny` | `python -m jcvi.graphics.synteny` | 多物种共线性对齐图 |
| `graphics_dotplot` | `python -m jcvi.graphics.dotplot` | 锚点 Dotplot |
| `graphics_karyotype` | `python -m jcvi.graphics.karyotype` | 物种内/两物种核型图 |
| `graphics_karyotype_global` | `python -m jcvi.graphics.karyotype` | 多物种全局核型总图 |
| `local_synteny` / `local_synteny_multi` | `python -m jcvi.compara.synteny query` | 以目标基因为中心的局部共线性 |
| `mcscan_pairwise` | `python -m jcvi.compara.synteny mcscan` | MCscan 两两共线性计算 |
| `catalog_ortholog` | `python -m jcvi.compara.catalog ortholog` | 共线性 + RBH 直系同源识别 |

以下候选功能均按**与上述基线的相似度**、**新增数据格式/依赖数量**、**GUI 适配成本**评估难度。

---

## 2. 按集成难度排序的候选功能

### 2.1 简单（Easy）：输入输出与现有工作流高度相似

这些功能大多为**单一文件进、单一图形/表格出**，或可直接复用现有 BED/FASTA/BLAST 输入。

| 功能 | 生物学意义 | 原 JCVI Linux 命令 | 集成思路 |
|---|---|---|---|
| **Heatmap 热图** | 展示基因表达、共线性分数、染色体尺度统计量等矩阵数据。 | `python -m jcvi.graphics.heatmap data.csv` | 新增 `graphics_heatmap` workflow，接收 CSV/matrix + 可选行/列注释，输出 PNG。 |
| **Histogram 直方图** | 快速查看 Ks、基因长度、覆盖度等数值分布。 | `python -m jcvi.graphics.histogram numbers.txt` | 新增 `graphics_histogram` workflow，输入单列/多列数值文件。 |
| **BLAST Dotplot** | 直接从 BLAST 结果画共线性点图，无需先生成 anchors。 | `python -m jcvi.graphics.blastplot blastfile --qsizes q.sizes --ssizes s.sizes` | 与 `graphics_dotplot` 共用 manifest，只需新增 `--blast` 输入选项。 |
| **MUMmer Dotplot** | 基于 MUMmer delta 文件画基因组比对点图，适合大尺度结构变异。 | `python -m jcvi.graphics.mummerplot deltafile` | 新增 `graphics_mummerplot` workflow，接收 `.delta` + sizes。 |
| **Coverage 覆盖度图** | 展示测序覆盖度沿染色体分布，评估测序均一性。 | `python -m jcvi.graphics.coverage chr sizes data` | 新增 `graphics_coverage` workflow，输入 BED/depth + sizes。 |
| **Table 表格图** | 将 CSV 统计表渲染为出版级表格图片。 | `python -m jcvi.graphics.table table.csv` | 新增 `graphics_table` workflow，适合报告汇总。 |
| **Gene Structure Glyph** | 从 GFF 绘制基因结构示意图（外显子、UTR、CDS）。 | `python -m jcvi.graphics.glyph gff` | 新增 `graphics_glyph` workflow，可用于局部共线性图旁注。 |
| **Synteny Matrix（Oxford Grid）** | 基于锚点生成 Oxford 网格，展示染色体间共线性密度。 | `python -m jcvi.compara.synteny matrix anchorsfile` | 作为 `mcscan_pairwise` 的衍生输出，直接在 artifacts 中附加 matrix 图。 |
| **Synteny Depth** | 计算并可视化两个基因组间的共线性深度，识别重复/缺失区段。 | `python -m jcvi.compara.synteny depth anchorsfile` | 新增独立 workflow 或在 `mcscan_pairwise` 后作为 QC 报告。 |
| **Synteny Stats / Summary** | MCscan 区块统计（数量、长度、覆盖度），用于 QC 报告。 | `python -m jcvi.compara.synteny stats anchorsfile`<br>`python -m jcvi.compara.synteny summary anchorsfile` | 直接作为 `mcscan_pairwise` 的 artifacts 输出，无需新增 workflow 文件。 |
| **Tandem Genes** | 识别串联重复基因簇，研究基因家族扩张与功能分化。 | `python -m jcvi.compara.catalog tandem pairsfile` | 新增 `catalog_tandem` workflow，输入 BLAST/BED，输出串联基因列表与图。 |
| **FASTA/BED/GFF/BLAST 工具箱** | 格式转换、过滤、合并、排序、提取等日常预处理。 | `python -m jcvi.formats.fasta extract seq.fa ids.txt`<br>`python -m jcvi.formats.bed merge a.bed b.bed`<br>`python -m jcvi.formats.gff bed input.gff`<br>`python -m jcvi.formats.blast best blastfile` | 统一包装为 `genomelens utils <format> <action>` CLI；每个 action 对应一个轻量 wrapper。 |
| **Annotation Stats** | 从 GFF 统计外显子/内含子长度、基因密度等注释质量指标。 | `python -m jcvi.annotation.stats stats genes.gff` | 新增 `annotation_stats` workflow，输出 JSON/TSV 报告。 |
| **Restriction Map** | 模拟限制性酶切图谱，评估组装完整性或构建物理图谱。 | `python -m jcvi.apps.restriction digest seq.fa --enzyme EcoRI` | 新增 `restriction_map` workflow，输入 FASTA，输出酶切位点图。 |
| **Assembly N50** | 快速计算 N50、L50 等组装统计量。 | `python -m jcvi.assembly.base n50 contigs.fa` | 可并入 `assembly_qc` workflow 或作为 `utils` 子命令。 |

#### 集成共性

- 大多只需新增一个 `engines/jcvi/src/jcvi_genomelens/workflows/*.py`。
- Manifest 选项可复用 `EngineRunManifest` 中的 `tracks`、`formats`、`figsize`、`dpi`。
- CLI 侧通过 `analyze workflow <onestop_id>`、`analyze submodule <module_id>` 或新增顶层命令组（如 `genomelens assembly`）暴露。
- GUI 可作为“新增一张图”卡片，无需改动核心分析流程。

---

### 2.2 中等（Medium）：需要新输入格式或额外依赖

这些功能对 GenomeLens 的现有流程是**自然延伸**，但需要新增 manifest 字段、外部工具或数据文件。

| 功能 | 生物学意义 | 原 JCVI Linux 命令 | 集成思路 |
|---|---|---|---|
| **Phylogenetic Tree** | 绘制 Newick 系统发育树；可叠加 GFF 基因结构，展示基因家族演化。 | `python -m jcvi.graphics.tree newicktree --gffdir gffs/` | 新增 `graphics_tree` workflow；manifest 增加 `newick` 路径与可选 `gff_dir`。 |
| **Chromosome Map** | 在染色体上绘制不同功能类别（基因、TE、GC 等），展示基因组组成。 | `python -m jcvi.graphics.chromosome bedfile mappings --sizes sizes.txt` | 新增 `graphics_chromosome` workflow；需要 BED + 类别映射文件。 |
| **Genome Landscape** | 多线/堆叠图展示基因密度、TE 密度、GC 含量等沿染色体分布。 | `python -m jcvi.graphics.landscape stack ...` | 新增 `graphics_landscape` workflow；支持多种子模式（stack/depth/heatmap）。 |
| **Ribbon Synteny** | 用 Ribbon（带状）图展示染色体间同源区段，比普通 synteny 图更直观。 | `python -m jcvi.graphics.ribbon blocks.bed layout.csv` | 新增 `graphics_ribbon` workflow；需要 blocks BED + layout CSV。 |
| **Wheel Plot** | 径向/轮状图展示连续数据（如共线性覆盖、表达量）。 | `python -m jcvi.graphics.wheel wheel ...` | 新增 `graphics_wheel` workflow，适合全局概览。 |
| **Assembly QC Graphics** | A50 曲线、覆盖度、scaffold 比对等组装质量可视化。 | `python -m jcvi.graphics.assembly A50 fastas/`<br>`python -m jcvi.graphics.assembly coverage ...` | 新增 `graphics_assembly` workflow；输入 FASTA/BAM/AGP。 |
| **BLAST Filter** | 在 synteny 前过滤局部重复、低 C-score 命中，提高锚点质量。 | `python -m jcvi.compara.blastfilter blastfile --qbed q.bed --sbed s.bed` | 作为 `mcscan_pairwise` 的预处理步骤或独立 `blastfilter` workflow。 |
| **Ks Analysis** | 计算同义替换率分布，识别全基因组复制（WGD）事件。 | `python -m jcvi.compara.ks ...` | 新增 `ks_analysis` workflow；需安装 `Bio.Align.Applications` 等依赖。 |
| **QUOTA-ALIGN** | 用整数规划筛选 1:1 / N:M 共线性区块，过滤旁系同源噪音。 | `python -m jcvi.compara.quota anchorsfile --qbed q.bed --sbed s.bed --quota 1:1` | 新增 `quota_align` workflow，与 `mcscan_pairwise` 输出衔接。 |
| **SynFind** | 为每个基因查找 syntenic region，构建基因级共线性网络。 | `python -m jcvi.compara.synfind blastfile --qbed q.bed --sbed s.bed` | 新增 `synfind` workflow，输出 per-gene synteny 表。 |
| **Phylogeny Orthologs** | 从 OrthoFinder 结果收集低拷贝直系同源组，用于系统发育构建。 | `python -m jcvi.compara.phylogeny lcn ...` | 新增 `phylogeny_orthologs` workflow，与 `catalog_ortholog` 联动。 |
| **K-mer Analysis** | K-mer 频数分布与基因组大小、杂合度估算。 | `python -m jcvi.assembly.kmer count reads.fq` | 新增 `kmer_analysis` workflow；输入 FASTQ/FASTA。 |
| **Genetic Map Integration** | 将遗传图谱锚定到物理组装，生成锚定图与热图。 | `python -m jcvi.assembly.geneticmap anchor ...` | 新增 `genetic_map` workflow；输入遗传图谱 + 物理 FASTA/BED。 |
| **Annotation QC** | 检测 NMD、UTR 修剪、重叠基因等注释问题。 | `python -m jcvi.annotation.qc uniq genes.gff` | 新增 `annotation_qc` workflow。 |
| **SNP Calling** | 封装 freebayes/GATK/samtools mpileup 的 SNP  calling 流程。 | `python -m jcvi.variation.snp gatk ...`<br>`python -m jcvi.variation.snp freebayes ...` | 新增 `snp_calling` workflow；需 BAM/参考基因组，依赖较多。 |
| **Data Fetch** | 从 NCBI/Ensembl/Phytozome 批量下载序列与注释。 | `python -m jcvi.apps.fetch entrez ...`<br>`python -m jcvi.apps.fetch phytozome ...` | 包装为 `genomelens fetch <source>` CLI，受网络与 API 限制。 |

#### 集成共性

- 需要在 `EngineRunManifest` 中新增字段（如 `newick`、`enzyme`、`quota`、`genetic_map`）。
- 部分依赖（`Bio.Align.Applications`、GATK、freebayes）需在 conda env 或文档中声明。
- 建议通过 `analyze submodule <module_id>` 扩展，或新增独立命令组（如 `genomelens assembly`、`genomelens annotation`）。
- GUI 需要新增配置面板，但逻辑与现有分析向导模式一致。

---

### 2.3 困难（Hard）：涉及复杂流程或多条外部依赖

这些功能代表 JCVI 的高级能力，但集成成本高，建议作为**独立模块**或**未来大版本**目标。

| 功能 | 生物学意义 | 原 JCVI Linux 命令 | 集成思路 |
|---|---|---|---|
| **Fractionation（基因丢失分析）** | 分析多倍化后两个亚基因组间的基因保留/丢失模式。 | `python -m jcvi.compara.fractionation loss ...` | 新增 `fractionation` workflow；输入 synteny blocks + GFF + 物种树，输出保留/丢失矩阵。 |
| **Ancestral Reconstruction** | 基于共线性区块重建祖先基因组顺序。 | `python -m jcvi.compara.reconstruct fuse ...` | 新增 `ancestral_reconstruct` workflow；属于高级比较基因组学。 |
| **PAD / Segmental Duplication** | 识别候选片段重复（PADs）。 | `python -m jcvi.compara.pad pad ...` | 新增 `pad_analysis` workflow，需要较多参数调优。 |
| **Ortho-Groups / OMG Enrich** | 将锚点聚类为直系同源群，并补充漏检基因。 | `python -m jcvi.compara.catalog group ...`<br>`python -m jcvi.compara.catalog enrich ...` | 在 `catalog_ortholog` 基础上扩展，但算法与输入更复杂。 |
| **ALLMAPS** | 利用多张遗传/物理图谱对 scaffold 进行排序与定向。 | `python -m jcvi.assembly.allmaps ...` | 新增独立 `allmaps` 模块；需安装 `cmmodule`。 |
| **Hi-C Scaffolding** | 基于 Hi-C 互作图谱进行染色体挂载。 | `python -m jcvi.assembly.hic ...` | 新增独立 `hic_scaffolding` 模块；需 `deap` 与大量计算资源。 |
| **Assembly Preprocess/Postprocess** |  reads 质控、去污染、去冗余、染色体化等完整流程。 | `python -m jcvi.assembly.preprocess trim ...`<br>`python -m jcvi.assembly.postprocess dedup ...` | 建议作为独立 pipeline（如 `genomelens assembly-pipeline`），而非单个 workflow。 |
| **MAKER / PASA / EVM** | 真核生物基因注释流水线。 | `python -m jcvi.annotation.maker parallel ...`<br>`python -m jcvi.annotation.pasa assemble ...`<br>`python -m jcvi.annotation.evm ...` | 属于独立注释模块，需配置大量外部工具（Augustus、SNAP、GeneMark 等）。 |
| **Automated Annotation** | RNA-seq 比对 + 转录本组装 + 基因预测一体化。 | `python -m jcvi.annotation.automaton star ...` | 新增 `automated_annotation` pipeline，依赖 STAR/Cufflinks/Augustus。 |
| **CNV / SV / Phasing / Imputation** | 拷贝数变异、结构变异、单倍型分相、基因型推断。 | `python -m jcvi.variation.cnv ...`<br>`python -m jcvi.variation.delly ...`<br>`python -m jcvi.variation.phase ...`<br>`python -m jcvi.variation.impute ...` | 建议独立 `variation` 模块；依赖 `pybedtools`、`pysam`、`pyliftover` 等。 |

#### 集成共性

- 通常需要新增独立的 engine manifest 模型与 CLI 命令组。
- 外部依赖复杂，必须在 `environment.yml` / 安装文档中明确说明。
- GUI 侧需要专门向导，不宜硬塞进现有 MCscan 分析流程。
- 建议以插件或可选扩展包形式提供，避免核心包臃肿。

---

## 3. 推荐优先级

### 短期（1–2 个迭代）：快速增强可视化与 QC

1. **Synteny Stats / Summary / Depth**：直接作为 `mcscan_pairwise` 的 artifacts，无新增 workflow 文件。
2. **BLAST Dotplot / MUMmer Dotplot**：与现有 dotplot 共用结构，丰富输入来源。
3. **Histogram / Heatmap / Coverage**：通用图形，CLI/GUI 均可快速接入。
4. **Tandem Genes**：与 `catalog_ortholog` 同属 `compara.catalog`，输入输出清晰。
5. **FASTA/BED/GFF/BLAST 工具箱**：作为 `genomelens utils` 子命令，提升日常工作效率。

### 中期（2–4 个迭代）：扩展比较基因组学能力

1. **Ks Analysis**：WGD 事件识别，生物学价值高，依赖可接受。
2. **QUOTA-ALIGN**：提升 synteny 结果质量，与现有流程衔接紧密。
3. **SynFind**：构建基因级共线性网络，支撑局部共线性改进。
4. **Graphics Tree / Ribbon / Chromosome / Landscape**：丰富出版物级图形。
5. **Annotation Stats / QC**：面向基因组注释质量评估用户。

### 长期（大版本或插件化）

1. **ALLMAPS / Hi-C Scaffolding**：独立 assembly 模块。
2. **Fractionation / Ancestral Reconstruction**：高级比较基因组学模块。
3. **MAKER/PASA/EVM / Automated Annotation**：独立注释模块。
4. **Variation 系列**：独立变异分析模块。

---

## 4. 环境依赖缺口

当前 `genomelens` conda 环境缺少以下包/工具，若集成对应功能需先行补齐：

| 依赖 | 影响功能 |
|---|---|
| `Bio.Align.Applications` / `Bio.Emboss.Applications` | `compara.ks`、`apps.phylo` |
| `cmmodule` | `assembly.allmaps` |
| `deap` | `assembly.hic`、`algorithms.ec` |
| `pybedtools` | `variation.cnv` |
| `pyfasta` | `variation.str` |
| `pyliftover` | `variation.impute`、`formats.vcf` |
| `pysam` | `variation.phase`、`formats.sam` 部分功能 |
| `boto3` | `variation.delly`、`utils.aws` |
| `bx-python` | `formats.maf` |
| `pyefd` / ImageMagick | `graphics.grabseeds`（非比较基因组学，建议不集成） |

---

## 5. 集成实施模板

以新增一个 JCVI workflow 为例，标准步骤如下：

1. **Engine 层**
   - 在 `engines/jcvi/src/jcvi_genomelens/workflows/` 新增 `xxx.py`。
   - 定义 `run(manifest: EngineRunManifest, outdir) -> tuple[list[CommandAudit], dict[str, object]]`。
   - 复用 `jcvi_genomelens.workflows.common._assert_ok`。

2. **Manifest 层**
   - 如需新增选项，在 `engines/jcvi/src/jcvi_genomelens/manifest_models.py` 扩展 `EngineRunOptions` 或新建 dataclass。

3. **Engine Contract 层**
   - 在平台侧 engine contract / runner 中注册 workflow 名称与参数映射。

4. **CLI 层**
   - 在 `platform/src/genomelens/cli/commands/analyze.py` 或新增 `utils.py` 中添加子命令。
   - 复用现有 `--workdir`、`--formats`、`--figsize`、`--dpi` 等通用参数。

5. **测试层**
   - 单元测试：参数解析、manifest 构建。
   - 集成测试：参考 `engines/jcvi/tests/test_engine_run.py`，验证输出文件非空。

6. **文档层**
   - 更新 `docs/用户手册.md`、`docs/使用方法/JCVI能力与配置.md`、`docs/更新计划/更新日志.md`。

---

## 6. 结论

GenomeLens 已经覆盖了 JCVI 最核心的比较基因组学可视化与分析能力。下一阶段最划算的扩展方向是：

- **先做“图形与 QC”**：Stats/Summary、Depth、BLAST/MUMmer Dotplot、Heatmap、Histogram。
- **再做“比较基因组学增强”**：Ks、QUOTA-ALIGN、SynFind、Tandem、Tree/Ribbon/Chromosome。
- **最后插件化攻坚**：Assembly、Annotation、Variation 等完整流水线。

这样既能持续扩大平台价值，又能保持核心包体积与依赖可控。
