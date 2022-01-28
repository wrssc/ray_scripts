# Import required Image library
from PIL import Image

factor = 0.25

in_images = [
    "development\\DITTO\\images\\red_circle.png",
    "development\\DITTO\\images\\green_circle.png",
    "development\\DITTO\\images\\blue_circle.png",
]

out_images = [
    "development\\DITTO\\images\\red_circle_icon.png",
    "development\\DITTO\\images\\green_circle_icon.png",
    "development\\DITTO\\images\\blue_circle_icon.png",
]

params = zip(in_images, out_images)

for img_in, img_out in params:

    # Create an Image Object from an Image
    im = Image.open(img_in)

    # Make the new image half the width and half the height of the original image
    resized_im = im.resize((round(im.size[0]*factor), round(im.size[1]*factor)))

    # Save the cropped image
    resized_im.save(img_out)
