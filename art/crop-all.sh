#!/bin/bash

mogrify -trim +repage -colorspace RGB ./*/*.png
