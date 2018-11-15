from typing import Union

import numpy as np
import pandas as pd
from scipy.sparse import spmatrix
from scipy.stats import chisquare
from statsmodels.stats.multitest import multipletests
from anndata import AnnData


def kbet(
    adata: AnnData,
    batch_key: str = 'batch',
    *,
    alpha: float = .05,
    adjacency: spmatrix = None,
    copy: bool = False,
) -> Union[AnnData, float]:
    """kBET: k-nearest neighbour batch effect test.

    Use the heuristic :func:`sc.pp.kbet_n_neighbors` to find the ideal
    neighborhood size to pass to :func:`sc.pp.neighbors`.

    Parameters
    ----------
    adata
        Annotated data matrix.
    batch_key
        The column in :attr:`anndata.AnnData.uns` to use as batch ID.
    alpha
        family-wise error rate. If p > ``alpha`` for the χ²-test on the neighborhood which to consider
    adjacency
        Sparse adjacency matrix of the graph, defaults to
        ``adata.uns['neighbors']['connectivities']``.
    copy
        Copy instance before computation and return a copy.
        Otherwise, perform computation in-place and return the kBET score.

    Returns
    -------
    adata
        If ``copy == True``, a copy of the input ``adata`` will be returned.
        Else, ``adata.uns['kbet']`` will contain the score.
    score
        If ``copy == False``, the kBET score is returned.
    """
    if adjacency is None:
        if 'neighbors' not in adata.uns:
            raise ValueError('No neighbors found. Provide the `adjacency` parameter or run `sc.pp.neighbors(adata)`')
        adjacency = adata.uns['neighbors']['connectivities']  # type: spmatrix
    adjacency = adjacency.tocsr()

    n_obs = adata.n_obs
    batch_ids = pd.Categorical(adata.obs[batch_key])
    # dof = len(batch_ids.unique()) - 1

    freqs_all = batch_ids.value_counts().sort_index() / len(batch_ids)
    freqs_neighbors = np.ndarray((n_obs, len(batch_ids.categories)))

    mask = adjacency != 0
    # cat_2d = np.tile(batch_ids, (n_obs, 1))
    # mapped = np.where(mask.A, cat_2d, None)
    for obs_i in range(n_obs):
        row_idx = mask[:, obs_i].A.flatten()
        freqs_obs = batch_ids[row_idx].value_counts().sort_index() / row_idx.sum()
        freqs_neighbors[obs_i, :] = freqs_obs

    _, p_vals_uncor = chisquare(freqs_neighbors, freqs_all, axis=1)
    rejected, p_vals, *_ = multipletests(p_vals_uncor, alpha)
    rate_rej = rejected.sum() / len(p_vals)

    rate_acc = 1 - rate_rej
    if copy:
        ad_ret = adata.copy()
        ad_ret.uns['kbet'] = rate_acc  # TODO: column for e.g. kbet-per-louvain
        return ad_ret
    else:
        return rate_acc
