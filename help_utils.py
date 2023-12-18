from glob import glob
import io
import numpy as np
import pandas as pd
from PIL import Image


async def images_to_grid(images, n_rows=3, n_cols=3, padding=10):
    """ Transform base64 images to numpy arrays, and puts them on a 3 by 3 grid in a single image. """
    # Transform bytes to arrays
    image_arrays = [np.array(Image.open(io.BytesIO(img))) for img in images]

    # Make sure all arrays are the same size
    assert len(set([a.shape for a in image_arrays])) == 1, "Images not all the same shape"
    # Make sure images are square
    assert image_arrays[0].shape[0] == image_arrays[0].shape[1], "Images are not square"
    # Make sure images have 3 dimensions (don't want to handle 2d images)
    assert image_arrays[0].shape[2] == 3, "Images are not 3 dimensional"

    # Only need one size, as we know the images are square
    img_size = image_arrays[0].shape[0]

    # Create empty image full of 200 (light gray pixels)
    grid_img_width = (n_cols * img_size) + ((n_cols - 1) * padding)
    grid_img_height = (n_rows * img_size) + ((n_rows - 1) * padding)
    grid_img = np.full(shape=(grid_img_height, grid_img_width, 3), fill_value=200)

    # One by one add separate images to large image array, calculating start and end
    # positions using x and y steps, image size, and padding size
    for y in range(n_rows):
        for x in range(n_cols):
            grid_img[(y * img_size) + (y * padding): (y + 1) * img_size + (y * padding),
                     (x * img_size) + (x * padding): (x + 1) * img_size + (x * padding),
                     :] = image_arrays[x + y]

    # Turn array into pillow Image object for easy saving
    # Array needs to be int, otherwise pillow raises exception
    grid_img = Image.fromarray(grid_img.astype(np.uint8))

    return grid_img
