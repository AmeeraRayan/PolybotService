import unittest
from polybot.img_proc import Img
import os

img_path = 'polybot/test/photos/beatles.jpeg' if '/polybot/test' not in os.getcwd() else 'photos/beatles.jpeg'

class TestImgContour(unittest.TestCase):

    def setUp(self):
        self.img = Img(img_path)
        self.original_img = Img(img_path)

    def test_contour_dimension(self):
        self.img.contour()
        actual_dimension = (len(self.img.data), len(self.img.data[0]))
        expected_dimension = (len(self.original_img.data), len(self.original_img.data[0]) - 1)
        self.assertEqual(expected_dimension, actual_dimension)

    def test_contour_effect(self):
        self.img.contour()
        differences = sum(
            1 for row1, row2 in zip(self.original_img.data, self.img.data)
              for pixel1, pixel2 in zip(row1[:len(row2)], row2) if pixel1 != pixel2
        )
        self.assertGreater(differences, 0)

if __name__ == '__main__':
    unittest.main()
