#!/usr/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import scipy as sp, scipy.sparse, scipy.linalg, scipy.sparse.linalg
from vresutils import indicator

def positive(a):
    if hasattr(a, "multiply"):
        if sp.sparse.isspmatrix_csc(a) or sp.sparse.isspmatrix_csr(a):
            m = a.__class__((positive(a.data), a.indices.copy(), a.indptr.copy()),
                            shape=a.shape, dtype=a.dtype)
            m.eliminate_zeros()
            return m
        else:
            return a.multiply(a>0)
    else:
        return a * (a>0)

def negative(a):
    if hasattr(a, "multiply"):
        if sp.sparse.isspmatrix_csc(a) or sp.sparse.isspmatrix_csr(a):
            m = a.__class__((negative(a.data), a.indices.copy(), a.indptr.copy()),
                            shape=a.shape, dtype=a.dtype)
            m.eliminate_zeros()
            return m
        else:
            return - a.multiply(a<0)
    else:
        return - a * (a<0)

def spdiag(v, k=0):
    if k == 0:
        N = len(v)
        inds = np.arange(N+1, dtype=np.int32)
        return sp.sparse.csc_matrix((v, inds[:-1], inds), (N, N))
    else:
        return sp.sparse.diags((v,),(k,))

def densify(a):
    """Return a dense array version of a """
    if sp.sparse.issparse(a):
        a = a.todense()
    return np.asarray(a)

def interpolate(a, axis=0):
    """Interpolate NaN values"""
    def interpolate1d(y):
        nan = np.isnan(y)
        x = lambda z: z.nonzero()[0]
        y[nan] = np.interp(x(nan), x(~nan), y[~nan])
        return y
    a = np.apply_along_axis(interpolate1d, axis, a)
    return a

def disable_sparse_safety_checks():
    import scipy.sparse, scipy.sparse.compressed

    def _check_format(s, full_check=True): pass
    scipy.sparse.compressed._cs_matrix.check_format = _check_format

    def _get_index_dtype(arrays=[], maxval=None, check_contents=False):
        return np.int32
    scipy.sparse.csc.get_index_dtype = _get_index_dtype
    scipy.sparse.csr.get_index_dtype = _get_index_dtype
    scipy.sparse.compressed.get_index_dtype = _get_index_dtype

def strikeoutxy(L, n):
    return np.asarray(np.bmat(((L[:n  ,:n], L[ :n ,n+1: ]),
                               (L[n+1:,:n], L[n+1:,n+1:]))))

def pinv(L, n):
    Lt = strikeoutxy(L, n)
    Li = sp.linalg.inv(Lt)
    dt = Li.dtype
    m = len(Lt)-n
    return np.asarray(np.bmat(((Li[:n,:n], np.zeros((n,1)), Li[:n,n:]),
                               (np.zeros((1,n)), np.zeros((1,1)), np.zeros((1,m))),
                               (Li[n:,:n], np.zeros((m,1)), Li[n:,n:]))))

def strikeoutx(L, n):
    hstack = sp.sparse.hstack if sp.sparse.isspmatrix(L) else np.hstack
    return hstack((L[:,:n], L[:,n+1:]))

def pinv2(L, n):
    Lt = strikeoutx(L, n)
    Li = np.empty_like(L)
    N = L.shape[1]
    for i in np.arange(N):
        sol = sp.sparse.linalg.bicg(Lt, indicator(N, i))
        Li[:n,i] = sol[:n]
        Li[n,i] = 0.
        Li[n+1:,i] = sol[n:]

    return Li
