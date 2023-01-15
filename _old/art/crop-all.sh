#!/bin/bash

find -type f -regex '[^\-]*' -exec mogrify -trim +repage -colorspace RGB {} +
