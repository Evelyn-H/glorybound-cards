#!/bin/bash

find -type f -regex '[^\-]*' -exec mogrify -trim +repage -colorspace RGB {} +


# mogrify -alpha extract -threshold 0 -negate -transparent white *
