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

plt.rcParams["svg.fonttype"] = "none"

# %%

results_file = "hotspot/hotspot_pairs_z.txt.gz"
results_hs_file = "hotspot/hotspot_hvg.txt"

MIN_CLUSTER_GENES = 50
MIN_CLUSTER_Z = 7

results = pd.read_table(results_file, index_col=0)
results_hs = pd.read_table(results_hs_file, index_col=0)

ens_map = {x: y for x, y in zip(results_hs.index, results_hs.Symbol)}

# %% Compute Linkage and Ordering

from scipy.spatial.distance import squareform
dd = results.copy().values
np.fill_diagonal(dd, 0)
condensed = squareform(dd)*-1
offset = condensed.min() * -1
condensed += offset
Z = linkage(condensed, method='average')

ii = leaves_list(Z)
ig = results.index[ii]

# %% Plot all distances
colors = list(plt.get_cmap("tab10").colors)
colors = [list(x) for x in colors]
distances = np.arange(-10, 50)

c_all = []
for dd in tqdm(distances):
    clusters = fcluster(Z, t=dd*-1+offset, criterion="distance")
    clusters = pd.Series(clusters, index=results.index)
    c_all.append(clusters)

# This section is to make it so that the same cluster has the same
# color as we go through the plot

def to_groups(cluster_series):
    groups = {}
    for g, i in cluster_series.iteritems():
        if i not in groups:
            groups[i] = set()

        groups[i].add(g)

    return groups


for i in tqdm(np.arange(len(c_all)-1)[::-1]):
    clusters = c_all[i]
    clusters_next = c_all[i+1]
    c_groups = to_groups(clusters)
    c_groups_next = to_groups(clusters_next)

    val_map = {}
    for k, vals in c_groups.items():
        max_overlap = -1
        max_j = -1
        for j, vals_n in c_groups_next.items():
            overlap = len(vals_n & vals)
            if overlap > max_overlap:
                max_j = j
                max_overlap = overlap

        val_map[k] = max_j

    c_all[i] = clusters.map(val_map)

# Now map most common to the top colors in the cmap
from collections import Counter
common = Counter(np.concatenate([x.values for x in c_all])).most_common()
common_map = {x[0]: i for i, x in enumerate(common)}

c_all = [x.map(common_map) for x in c_all]

row_colors_all = []
for clusters in c_all:
    row_colors_i = pd.Series(
        [colors[i % len(colors)] for i in clusters], index=results.index
    )
    row_colors_all.append(row_colors_i)

row_colors_all = pd.concat(row_colors_all, axis=1)
row_colors_all.columns = ["{:.2f}".format(x) for x in distances]
row_colors_all = row_colors_all.loc[ig]
# Need to turn this into NxMx3
cvals = np.zeros((row_colors_all.shape[0], row_colors_all.shape[1], 3))
for i in range(cvals.shape[0]):
    for j in range(cvals.shape[1]):
        cvals[i, j, :] = row_colors_all.iloc[i, j]

plt.figure()
plt.imshow(cvals, aspect="auto")
label_ii = np.arange(0, cvals.shape[1], 5)
plt.xticks(ticks=label_ii, labels=row_colors_all.columns[label_ii], rotation=90)
label_jj = np.arange(0, cvals.shape[0])
plt.yticks(ticks=label_jj, labels=[ens_map[x] for x in row_colors_all.index])
plt.subplots_adjust(bottom=.15)
plt.show()

# %% Compute gene clusters

# clusters = fcluster(Z, t=15, criterion='maxclust')
clusters = fcluster(Z, t=MIN_CLUSTER_Z*-1+offset, criterion="distance")
clusters = pd.Series(clusters, index=results.index)

vcs = clusters.value_counts()

valid_clusters = vcs.index[vcs >= MIN_CLUSTER_GENES]
valid_cluster_map = {x: i + 1 for i, x in enumerate(valid_clusters)}
valid_cluster_map[-1] = -1

clusters[[x not in valid_clusters for x in clusters]] = -1
clusters = clusters.map(valid_cluster_map)
valid_clusters = [x for x in valid_cluster_map.values() if x != -1]

cluster_map = {k: set(v.index) for k, v in clusters.groupby(clusters)}

# %% Plot the clusters

colors = list(plt.get_cmap("tab10").colors)
cm = ScalarMappable(norm=Normalize(0, 0.05, clip=True), cmap="viridis")
row_colors1 = pd.Series(
    [colors[i % 10] if i != -1 else "#ffffff" for i in clusters],
    index=results.index,
)

row_colors = pd.DataFrame({"Cluster": row_colors1})

cm = sns.clustermap(
    results.iloc[ii, ii],
    row_cluster=False,
    col_cluster=False,
    vmin=-25,
    vmax=25,
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
plt.show()

# %% what about this other algorithm dynamicTreeCut

import dynamicTreeCut


dt_clusters = dynamicTreeCut.cutreeHybrid(
    link=Z, distM=condensed, minClusterSize=10
)

# %% Plot and compare results

colors = list(plt.get_cmap("tab10").colors)
cm = ScalarMappable(norm=Normalize(0, 0.05, clip=True), cmap="viridis")
row_colors1 = pd.Series(
    [colors[i % 10] if i != -1 else "#ffffff" for i in clusters],
    index=results.index,
)
row_colors2 = pd.Series(
    [colors[i % 10] if i != -1 else "#ffffff" for i in dt_clusters['labels']],
    index=results.index,
)

row_colors = pd.DataFrame({
    "Cluster": row_colors1,
    "Cluster-Dt": row_colors2,
})

cm = sns.clustermap(
    results,
    row_linkage=Z,
    col_linkage=Z,
    vmin=-25,
    vmax=25,
    cmap="RdBu_r",
    xticklabels=False,
    yticklabels=False,
    row_colors=row_colors,
    rasterized=True,
)

fig = plt.gcf()
fig.patch.set_visible(False)
plt.sca(cm.ax_heatmap)
plt.ylabel("")
plt.xlabel("")
plt.show()

# %% what if we sort by cluster labels?

new_ii = np.argsort(dt_clusters['labels'])

cm = sns.clustermap(
    results.iloc[new_ii, new_ii],
    metric='correlation',
    row_cluster=True,
    col_cluster=True,
    vmin=-55,
    vmax=55,
    cmap="RdBu_r",
    xticklabels=False,
    yticklabels=results_hs.Symbol.loc[results.index[new_ii]],
    row_colors=row_colors.iloc[new_ii],
    rasterized=True,
)

fig = plt.gcf()
fig.patch.set_visible(False)
plt.sca(cm.ax_heatmap)
plt.ylabel("")
plt.xlabel("")
plt.show()

# %% What are these clusters?

rc = results_hs.join(
    pd.Series(dt_clusters['labels'], index=results.index, name='Cluster')
)

rc.loc[rc.Cluster == 5].sort_values('Z').tail(20)
