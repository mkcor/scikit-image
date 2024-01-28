"""
==================================================
Segment 3D image sample of developing mouse embryo
==================================================

In this example, we look at a microscopy image of a developing mouse embryo.
We use sample data from [1]_, more precisely from embryo B at time point 184.

.. [1] McDole K, Guignard L, Amat F, Berger A, Malandain G, Royer LA,
       Turaga SC, Branson K, Keller PJ (2018) "In Toto Imaging and
       Reconstruction of Post-Implantation Mouse Development at the
       Single-Cell Level" Cell, 175(3):859-876.e33.
       ISSN: 0092-8674
       :DOI:`10.1016/j.cell.2018.09.031`

"""

import io
import requests

import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage as ndi

import skimage as ski


#####################################################################
# We downloaded the original data in KLB format and saved a selection thereof:
#
# .. code-block:: python
#
#     import numpy as np
#     import pyklb as klb
#
#     data = klb.readfull('Mmu_E1_CAGTAG1.TM000184_timeFused_blending/SPM00_TM000184_CM00_CM01_CHN00.fusedStack.corrected.shifted.klb')
#     sample = data[400:450, 1000:1750, 400:900]
#     np.save('sample_3D_frame_184', sample)

sample_url = 'https://github.com/mkcor/draft-notebooks/raw/main/embryo/data/sample_3D_frame_184.npy'
response = requests.get(sample_url)
im3d = np.load(io.BytesIO(response.content))

print(f'The shape of the image is: {im3d.shape}')

#####################################################################
# The dataset is a 3D image with 50 `xy` sections stacked along `z`. Let us
# visualize it by picking one such section in five.

data_montage = ski.util.montage(im3d[::5], grid_shape=(2, 5), padding_width=5)
fig, ax = plt.subplots(figsize=(10, 5))
ax.imshow(data_montage)
ax.set_axis_off()

# global thresholding vs local thresholding
global_thresh = ski.filters.threshold_otsu(im3d)
binary_global = im3d > global_thresh

block_size = 31
local_thresh = ski.filters.threshold_local(im3d, block_size)
binary_local = im3d > local_thresh

#####################################################################
# Let us view the mid-stack `xy` section.

fig, axes = plt.subplots(ncols=3, figsize=(12, 4))
ax = axes.ravel()

ax[0].imshow(im3d[25, :, :])
ax[0].set_title('Original')

ax[1].imshow(binary_global[25, :, :])
ax[1].set_title('Global thresholding (Otsu)')

ax[2].imshow(binary_local[25, :, :])
ax[2].set_title('Local thresholding')

for a in ax:
    a.axis('off')

#####################################################################
# We smooth out the locally thresholded image (which is binary), so we can
# in turn threshold it globally.

smooth = ski.filters.gaussian(binary_local, sigma=1.5)
thresholds = ski.filters.threshold_multiotsu(smooth, classes=3)
regions = np.digitize(smooth, bins=thresholds)

fig, ax = plt.subplots(ncols=2, figsize=(8, 4))
ax[0].imshow(smooth[25, :, :])
ax[0].set_title('Smoothing out')
ax[0].axis('off')
ax[1].imshow(regions[25, :, :])
ax[1].set_title('Multi-Otsu thresholding')
ax[1].axis('off')

#####################################################################
# We identify nuclei to be the brightest of the three classes and we remove
# small objects.

cells_noisy = smooth > thresholds[1]
cells = ski.morphology.opening(cells_noisy, footprint=np.ones((3, 5, 5)))

#####################################################################
# We use the watershed algorithm to find single nuclei when they are touching
# or overlapping.

distance = ndi.distance_transform_edt(cells)

local_max_coords = ski.feature.peak_local_max(distance, min_distance=12)
local_max_mask = np.zeros(distance.shape, dtype=bool)
local_max_mask[tuple(local_max_coords.T)] = True
markers = ski.measure.label(local_max_mask)

segmented_cells = ski.segmentation.watershed(-distance, markers, mask=cells)

fig, ax = plt.subplots(ncols=2, figsize=(10, 5))
ax[0].imshow(cells[25, :, :], cmap='gray')
ax[0].set_title('Touching nuclei')
ax[0].axis('off')
ax[1].imshow(ski.color.label2rgb(segmented_cells, bg_label=0)[25, :, :])
ax[1].set_title('Segmented nuclei')
ax[1].axis('off')

#####################################################################
# With the naked eye, we can see a slight over-segmentation... How does this
# segmentation compare with that obtained in [1]_?

#####################################################################
# We used the software developed for the research project at:
# (https://bitbucket.org/fernandoamat/tgmm-paper/src/master/doc/new/docs/user-guide/quickstart.md)
# We edited the TGMM config file to apply the hierarchical segmentation on
# the sample data, which we saved 'back' in KLB format:
#
# .. code-block:: python
#
#     klb.writefull(np.ascontiguousarray(sample), 'sample_3D_frame_184.klb')
#
# We installed the software (https://bitbucket.org/fernandoamat/tgmm-paper/src/master/doc/new/docs/dev-guide/building.md)
# and ran it:
#
# .. code-block:: bash
#
#     ProcessStack config.md 184
#     ProcessStack sample_3D_frame_184_seg_conn74_rad2.bin 14 50
#
# Chose tau=14 because persistanceSegmentationTau=14 in config file.
# A value of tau=2 clearly yiels oversegmentation (yields 1597 nuclei).
# Chose minSuperVoxelSzPx=50 because minNucleiSize=50 in config file.
# Not much difference between minSuperVoxelSzPx=50 (yiels 517 nuclei) and
# minSuperVoxelSzPx=14 (yiels 541 nuclei).
# The output (segmentation result) is a KLB file; we save it into a Numpy array.

res_url = 'https://github.com/mkcor/draft-notebooks/blob/main/embryo/data/tgmm_conn74_tau14.npy'
resp = requests.get(res_url)
gt = np.load(io.BytesIO(resp.content))

fig, ax = plt.subplots(ncols=2, figsize=(10, 5))
ax[0].imshow(ski.color.label2rgb(gt[25, :, :], bg_label=0))
ax[0].set_title('TGMM output')
ax[0].axis('off')
ax[1].imshow(ski.color.label2rgb(segmented_cells, bg_label=0)[25, :, :])
ax[1].set_title('Our output')
ax[1].axis('off')

#####################################################################
# The TGMM segmentation looks cleaner than ours, but it seems to be missing
# quite a few nuclei in the upper half of the `xy` section.
# Our *local* thresholding seems to be making the difference here.
# When enhancing the contrast of the original image, the nuclei in this darker
# area can be clearly seen:

enhanced_image = ski.exposure.equalize_hist(im3d[25, :, :])
fig, ax = plt.subplots()
ax.imshow(enhanced_image)
