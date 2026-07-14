# Domain pack: omics and bioinformatics figures

Use this file for RNA-seq, differential expression, GWAS, single-cell, expression
heatmaps, PCA/UMAP embeddings, volcano plots, Manhattan plots, and MA plots.

## Conventions

- For publication-facing outputs, use the target journal's current size, format,
  DPI, font, and transparency rules first, then the mechanisms in
  `references/scientific-figures.md`. Use `JOURNAL = "nat2"`, PDF, and 600 dpi
  TIFF only when the target venue, physical size, and explicit output requirements
  are all unknown.
- Prefer adjusted p values/FDR (`padj`, `qvalue`, `FDR`) over raw p values when
  available.
- Put thresholds in config and state them in the final response.
- Use muted gray for background points and one or two strong colors for highlights.
- For arrays of per-point colors, use hex codes or standard Matplotlib color names;
  avoid UltraPlot named colors inside NumPy arrays.
- Rasterize dense point clouds while keeping labels and axes vector.
- Label only a small reproducible set of genes/features, such as top significant hits.
- Use domain libraries when they are needed for clustering, single-cell structures, or
  specialized layouts; state the fallback reason.

Common config:

```python
LFC_COL = "log2FoldChange"
PADJ_COL = "padj"
PADJ_THRESHOLD = 0.05
LFC_THRESHOLD = 1.0
LABEL_TOP_N = 10
JOURNAL = "nat2"
DPI = 600
OUTPUT_STEM = "figure"  # set a distinct stem for each delivered figure
```

These output settings describe the fully unspecified fallback. Copy the canonical
standalone `save_publication_fallback(...)` function from
`references/scientific-figures.md` into the delivered script; do not import it from
the installed skill. The fallback examples below keep all production artists opaque.

Validation helpers:

```python
def numeric_column(df, col):
    values = pd.to_numeric(df[col], errors="coerce")
    if values.isna().any():
        raise ValueError(f"{col} contains non-numeric or missing values: {values.isna().sum()} rows")
    return values


def pvalue_column(df, col):
    values = numeric_column(df, col)
    bad = (values < 0) | (values > 1)
    if bad.any():
        raise ValueError(f"{col} contains p values outside [0, 1]: {bad.sum()} rows")
    return values
```

## Volcano plot

Required columns: log2 fold change and adjusted p value.

```python
lfc = numeric_column(df, LFC_COL)
padj = pvalue_column(df, PADJ_COL)
df["neg_log10_padj"] = -np.log10(padj.clip(lower=1e-300))

up = (padj < PADJ_THRESHOLD) & (lfc >= LFC_THRESHOLD)
down = (padj < PADJ_THRESHOLD) & (lfc <= -LFC_THRESHOLD)
# dtype=object avoids NumPy's fixed-width string truncation if a longer color
# string (e.g. 8-digit hex or a named color) is substituted later.
colors = np.full(len(df), "#8C8C8C", dtype=object)
colors[up.to_numpy()] = "#D55E00"
colors[down.to_numpy()] = "#0072B2"

fig, ax = uplt.subplots(journal=JOURNAL)
ax.scatter(lfc, df["neg_log10_padj"], c=colors, s=8, absolute_size=True,
           rasterized=True)
ax.axvline(-LFC_THRESHOLD, color="gray6", linestyle="--", linewidth=0.8)
ax.axvline(LFC_THRESHOLD, color="gray6", linestyle="--", linewidth=0.8)
ax.axhline(-np.log10(PADJ_THRESHOLD), color="gray6", linestyle="--", linewidth=0.8)
ax.format(xlabel="log2 fold change", ylabel="-log10 adjusted p", grid=True)
save_publication_fallback(fig, OUTPUT_STEM, dpi=DPI)
```

Label genes using a reproducible rule, for example the top `LABEL_TOP_N` genes among
significant hits ranked by adjusted p value and absolute log2 fold change.

## MA plot

```python
lfc = numeric_column(df, LFC_COL)
base_mean = numeric_column(df, "baseMean")
if (base_mean <= 0).any():
    raise ValueError("baseMean must be positive for a log-scaled MA plot")

fig, ax = uplt.subplots(journal=JOURNAL)
ax.scatter(base_mean, lfc, c="#8C8C8C", s=8, absolute_size=True,
           rasterized=True)
ax.axhline(0, color="black", linewidth=0.8)
ax.axhline(LFC_THRESHOLD, color="gray6", linestyle="--", linewidth=0.8)
ax.axhline(-LFC_THRESHOLD, color="gray6", linestyle="--", linewidth=0.8)
ax.format(xscale="log", xlabel="Mean expression", ylabel="log2 fold change", grid=True)
save_publication_fallback(fig, OUTPUT_STEM, dpi=DPI)
```

## Manhattan or GWAS plot

Precompute cumulative genomic position in preprocessing for large inputs. Validate p
values before transformation and use an explicit chromosome order.

```python
df["p"] = pvalue_column(df, "p")
df["neg_log10_p"] = -np.log10(df["p"].clip(lower=1e-300))

chrom_order = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
df["chrom"] = pd.Categorical(df["chrom"].astype(str), categories=chrom_order, ordered=True)
df = df.sort_values(["chrom", "pos"])

# cum_pos should usually be computed in preprocessing from chrom lengths or max positions.
fig, ax = uplt.subplots(journal=JOURNAL)
tick_positions = []
tick_labels = []
for i, (chrom, subset) in enumerate(df.groupby("chrom", observed=True, sort=True)):
    color = "#595959" if i % 2 == 0 else "#A6A6A6"
    ax.scatter(subset["cum_pos"], subset["neg_log10_p"], s=4,
               absolute_size=True, color=color, rasterized=True)
    tick_positions.append(float(subset["cum_pos"].median()))
    tick_labels.append(str(chrom))
ax.axhline(-np.log10(5e-8), color="#D55E00", linestyle="--", linewidth=0.8)
ax.format(xlabel="Chromosome", ylabel="-log10 p", xlocator=tick_positions,
          xticklabels=tick_labels, grid=True)
save_publication_fallback(fig, OUTPUT_STEM, dpi=DPI)
```

## Heatmap and embeddings

Use UltraPlot for ordered matrices:

```python
SHOW_CELL_LABELS = False  # enable only after final-size render QA

fig, ax = uplt.subplots(journal=JOURNAL)
ax.heatmap(
    zscores, cmap="vik", vmin=-3, vmax=3,
    labels=SHOW_CELL_LABELS, precision=2,
    labels_kw={"fontsize": "small"},
    colorbar="r", colorbar_kw={"label": "z score"},
)
ax.format(xlabel="Samples", ylabel="Genes")
save_publication_fallback(fig, OUTPUT_STEM, dpi=DPI)
```

Use `seaborn.clustermap`, `scanpy`, or another domain library when clustering,
dendrogram layout, or single-cell object handling is the core task.

Embedding:

```python
fig, ax = uplt.subplots(journal=JOURNAL)
for label, subset in df.groupby("cell_type", observed=True):
    ax.scatter(subset["UMAP1"], subset["UMAP2"], s=4, absolute_size=True,
               label=label, rasterized=True)
ax.legend(loc="r", frame=False)
ax.format(xlabel="UMAP1", ylabel="UMAP2")
save_publication_fallback(fig, OUTPUT_STEM, dpi=DPI)
```

For many cell types or clusters, avoid an unreadable legend. Use top categories,
external legends, direct labels at cluster centroids, or facets. An external
legend is not automatically collision-free: use physical internal spacing and run
final-draw legend geometry QA.

## QA

- Thresholds are explicit.
- Adjusted and raw p values are not confused.
- P values are validated before `-log10` transformation.
- Transformations are labeled (`log2`, `-log10`, z score, normalized expression).
- Gene labels use a reproducible rule and do not clutter the plot.
- Color semantics are stable across panels.
- Dense point clouds are rasterized; labels, axes, and panel letters remain vector.
- Heatmap cell labels, when enabled, remain readable at final physical size and use
  the built-in `labels`/`precision`/`labels_kw` interface.
- All legends pass final-draw collision and containment QA.
- Measured final size and saved formats follow the target venue; fallback use is
  reported explicitly.
