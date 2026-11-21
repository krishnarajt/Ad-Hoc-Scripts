#!/bin/bash

# Array of links
links=(
  "https://curiositystream.com/series/628"
  "https://curiositystream.com/series/642"
  "https://curiositystream.com/series/699"
  "https://curiositystream.com/series/739"
  "https://curiositystream.com/series/371"
  "https://curiositystream.com/series/806"
  "https://curiositystream.com/series/199"
  "https://curiositystream.com/series/491"
  "https://curiositystream.com/series/494"
  "https://curiositystream.com/series/803"
  "https://curiositystream.com/series/620"
  "https://curiositystream.com/series/545"
  "https://curiositystream.com/series/698"
  "https://curiositystream.com/video/1904"
  "https://curiositystream.com/series/396"
  "https://curiositystream.com/series/325"
  "https://curiositystream.com/series/288"
  "https://curiositystream.com/video/7775"
  "https://curiositystream.com/series/176"
  "https://curiositystream.com/series/440"
  "https://curiositystream.com/series/743"
  "https://curiositystream.com/series/577"
  "https://curiositystream.com/series/631"
  "https://curiositystream.com/series/521"
)

# Loop through each link
for link in "${links[@]}"
do
  # Extract the ID from the link
  id=$(echo $link | sed 's/.*\///')

  # Create a directory with the ID as the name
  mkdir $id
  echo $id $link  
  # Download audio format for the video
  yt-dlp $link -u kpt.krishnaraj@gmail.com -p curiosityhattori1618 --format hls-audio_group-English -o "$id/%(title)s.%(ext)s"
done
