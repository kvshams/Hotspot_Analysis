from scipy.cluster.hierarchy import linkage, leaves_list, fcluster
import numpy as np
import pandas as pd
import __main__ as main
if hasattr(main, '__file__'):
    import matplotlib
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import seaborn as sns
from tqdm import tqdm
import hotspot.modules
from statsmodels.stats.multitest import multipletests
from scipy.spatial.distance import squareform
from scipy.stats import norm

plt.rcParams["svg.fonttype"] = "none"

results_file = snakemake.input["results_z"]

MIN_CLUSTER_GENES = snakemake.params["min_cluster_genes"]  # 50
CORE_ONLY = snakemake.params["core_only"]  # 50

try:
    Z_THRESHOLD = snakemake.params["z_threshold"]
except AttributeError:
    Z_THRESHOLD = 3


cluster_heatmap_file = snakemake.output["cluster_heatmap"]
cluster_output_file = snakemake.output["cluster_output"]
linkage_output_file = snakemake.output["linkage_output"]

results = pd.read_table(results_file, index_col=0)

# Optionally, FDR Threshold overrides Z threshold
try:
    FDR_THRESHOLD = snakemake.params["fdr_threshold"]

    allZ = squareform(results.values/2 + results.values.T/2) # just in case slightly not symmetric
    allZ = np.sort(allZ)
    allP = norm.sf(allZ)
    allP_c = multipletests(allP, method='fdr_bh')[1]
    ii = np.nonzero(allP_c < FDR_THRESHOLD)[0][0]
    Z_THRESHOLD = allZ[ii]

    print(FDR_THRESHOLD, Z_THRESHOLD)

except AttributeError:
    pass

# %% Compute Linkage and Ordering

modules, Z = hotspot.modules.compute_modules(
    results, min_gene_threshold=MIN_CLUSTER_GENES,
    z_threshold=Z_THRESHOLD, core_only=CORE_ONLY
)

modules.rename('Cluster').to_frame().to_csv(cluster_output_file, sep="\t")
linkage_out = pd.DataFrame(Z).to_csv(
    linkage_output_file, header=False, index=False, sep="\t")


# %% Plot the clusters

from scipy.cluster.hierarchy import leaves_list
ii = leaves_list(Z)

colors = list(plt.get_cmap("tab10").colors)
cm = ScalarMappable(norm=Normalize(0, 0.05, clip=True), cmap="viridis")
row_colors1 = pd.Series(
    [colors[i % 10] if i != -1 else "#ffffff" for i in modules],
    index=results.index,
)

row_colors = pd.DataFrame({"Cluster": row_colors1})

cm = sns.clustermap(
    results.iloc[ii, ii],
    row_cluster=False,
    col_cluster=False,
    vmin=-15,
    vmax=15,
    cmap="RdBu_r",
    xticklabels=False,
    yticklabels=False,
    row_colors=row_colors.iloc[ii],
    rasterized=True,
)

fig = plt.gcf()
fig.patch.set_visible(False)
plt.sca(cm.ax_heatmap)
plt.ylabel("")
plt.xlabel("")
plt.savefig(cluster_heatmap_file, dpi=300)
# plt.show()
