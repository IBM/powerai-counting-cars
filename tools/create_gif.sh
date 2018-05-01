#!/bin/sh -e
# Copyright 2018 IBM All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ $# -eq 0 ]; then
    echo "Usage error: Specify the output directory as arg1."
fi

palette="/tmp/palette.png"
filters="fps=10,scale=320:-1:flags=lanczos"

ffmpeg -v warning -i "$1/output-video.mp4" -vf "$filters,palettegen=stats_mode=diff" -y $palette
ffmpeg -i "$1/output-video.mp4" -r "15" -i $palette -lavfi "$filters,paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y output/output-video-as-gif.gif

echo "Created gif \"$1/output-video-as-gif.gif\" from \"$1/output-video.mp4\""

