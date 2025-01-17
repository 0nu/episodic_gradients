import os, sys, glob
from nilearn import masking
import numpy as np
from scipy import spatial
import h5py as h5
from mapalign import embed
import argparse

subj_file = 'x_preprocessed.nii.gz'
img_mask  = 'rest_intra_mask_mni_gm_thr_YY.nii.gz'
out_prfx  = '/data/pt_neuam005/sheyma/test_thr60_scipy/x_preprocessed'

parser = argparse.ArgumentParser()
parser.add_argument('-l','--in', dest='sbj_file')
parser.add_argument('-m', '--mask', dest='mask_name')
parser.add_argument('-o', '--out', dest='out_prefix', type=str)

results  = parser.parse_args()
img_mask = results.mask_name
img_rest = results.sbj_file
out_prfx = results.out_prefix

#### Step 1 #### get connectivity matrix based on gray matter t-series
def mask_check(rest, mask):
    """
    rest: 4D nifti-filename
    mask: 3D nifti-filename
    """
    matrix = masking.apply_mask(rest, mask)
    matrix = matrix.T
    cnt_zeros = 0
    for i in range(0, matrix.shape[0]):
        if np.count_nonzero(matrix[i, :]) == 0:
            cnt_zeros += 1
    return cnt_zeros, matrix

[voxel_zeros, t_series] = mask_check(img_rest, img_mask)

if voxel_zeros > 0:
   print('complete-zeros timeseries!!! exiting...')
   sys.exit(1)

print('calculating correlation matrix...')
indiv_matrix = np.corrcoef(t_series)

print(img_rest)
print(indiv_matrix.shape)

#### Step 2 #### threhold at 90th percentile
print('thresholding each row at its 90th percentile...')
perc = np.array([np.percentile(x, 90) for x in indiv_matrix])
N    = indiv_matrix.shape[0]

for i in range(N):
    indiv_matrix[i, indiv_matrix[i,:] < perc[i]] = 0

#neg_values = np.array([sum(indiv_matrix[i,:] < 0) for i in range(N)])
#print('Negative values occur in %d rows' % sum(neg_values > 0))
indiv_matrix[indiv_matrix < 0] = 0

#### Step 3 #### compute the affinity matrix
print('calculating affinity matrix with scipy...')
indiv_matrix = spatial.distance.pdist(indiv_matrix, metric = 'cosine')
indiv_matrix = spatial.distance.squareform(indiv_matrix)
indiv_matrix = 1.0 - indiv_matrix

print('affinity shape ', np.shape(indiv_matrix))

#### Step 4 #### get gradients
print('computing gradients...')
# NOTE this is fast but uses a lot of memory. So if we would save the matrix
# here, then we could run everything above more parallel above all subjects
emb, res = embed.compute_diffusion_map(indiv_matrix, alpha = 0.5,
                                       n_components = 10,
                                       return_result=True)

out_name_emb = os.path.join(out_prfx + '_dense_emb.npy')
out_name_res = os.path.join(out_prfx + '_dense_res.npy')
print(out_name_emb)
np.save(out_name_emb, emb)
np.save(out_name_res, res['lambdas'])


