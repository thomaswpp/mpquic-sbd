# Create video for running the experiment

This folder contains example files and code for creating segments and representing mpd

Version:
  -- **MP4Box - GPAC version 2.0-rev2.0.0+dfsg1-2**
  -- **ffmpeg version 4.4.3-0ubuntu1~20.04.sav1**


## Quickstart

```
#Convert an mp4 video into videos of other formats and sizes using ffmpgeg
#In this example converting a 4k 60 fps video to a 240 MB 25 fps video
ffmpeg -y -i 4k60fps.mp4 -c:a aac -ac 2 -ab 128k -c:v libx264 -x264opts 'keyint=96:min-keyint=96:no-scenecut' -b:v 250k -maxrate 500k -bufsize 1000k -s 426x240 -vf scale=426x240 -filter:v fps=25 video_240_25fps.mp4 &
```

After converting the videos to the desired formats, we have to segment and create the mpd representation.

```
#In this example we are creating videos of 4 second segments along with their representative
MP4Box -dash 4000 \
-segment-name 'segment_$RepresentationID$_' \
-mpd-refresh 4 \
-fps 25 video_240_25fps.mp4#video:id=240p \
-fps 25 video_360_25fps.mp4#video:id=360p \
-fps 25 video_480_25fps.mp4#video:id=480p \
-fps 25 video_720_25fps.mp4#video:id=720p \
-fps 60 video_720_60fps.mp4#video:id=7202p \
-fps 25 video_1080_25fps.mp4#video:id=1080p \
-fps 60 video_1080_60fps.mp4#video:id=10802p \
-fps 30 video_1440_30fps.mp4#video:id=1440p \
-fps 60 video_1440_60fps.mp4#video:id=14402p \
-fps 30 video_2160_30fps.mp4#video:id=2560p \
-fps 60 video_2160_60fps.mp4#video:id=25602p \
-out output_dash.mpd
```

The SARA algorithm requires that the representative contain extra information for each segment, which MP4Box does not do, so a python code was created to modify the standard MPD created by MP4Box into the representative compatible with the SARA algorithm.

```
# the output_dash.mpd file is in the same folder as "modify_mpd.py"
python modify_mpd.py 
```
