# Old Main Versions

## Description 

* This directory archives previous versions of the main application script (`main.py`) and any other scripts use to analyse the difference between iterations. 
* All forms of filtering methodology (outside of the networkx mutlidigraph) can be found in this scripts. 

## Contents


*   `main_original.py`: The original version of the main script. The only filtering mechanism it used was creating a centroid with centre being the average position of all users, and the radius being the distance to the furthest user. This became deprecated once we implemented the convex hull + elliptical shape filtering mechanism. 
*   `main_comparison.py`: This is a comparison script for comparing the two forms of filtering done in `main_original.py` and our current `main.py` script. 
*   `debug_station_filtering.py`: A few bugs/errors were ran into when implementing ellipse filtering, this script was used to find those errors
*   `debug_compare_times.py`: A script to analyse why there was such a big difference between graph and TFL API journeytime. This was due to incorrect information being inputted to TFL API (coordiantes instead of station code) artificially adding a walking time. 
*   `main_copy.py`: This is our final main.py script before modularisation. 