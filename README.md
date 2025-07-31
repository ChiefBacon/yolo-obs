# OBS Object Detection
A simple Python program that can add YOLO object detection to OBS using OBS websockets.

## Setup
You need to have uv and Python 3.12 or newer. Start by installing dependencies with this command:
```shell
uv sync --extra cpu
```
If you want to run the object detection on the GPU instead of the CPU, run:
```shell
uv sync --extra gpu
```
This currently only works with NVIDIA GPUs. You will also have to update the following line of the config file.
```toml
UseGPU = no                ; Whether or not to use a CUDA GPU
```
---
Then you can run the program after setting up your config file by running
```shell
uv run src/main.py
```

> [!NOTE]  
> Docker images are planned for a future release.

### Camera Number Selection
Currently, there is no simple way to find the number for the camera that you want to use, so the process mostly just 
boils down to trial and error. Start with zero and work your way up until you find the correct camera. There are plans
to make this easier in a future release.

### Config
You can write a configuration file based on the example config file, then rename it to `obs-object-detection.ini`.

### Preview Window
The preview window shows the camera feed. Differently colored boxes are placed around different items in the frame. Blue
is a detected item from the main detection list. Red is a detected item from the disallow list. Green is a detected item
that is not in either list. The current framerate can optionally be shown in the top left corner of the preview window. 
To close the program, you can press the escape key while the preview window is focused.

## Support
If you have any issues, just add an issue on the GitHub page.

## Future Plans
Planned features for the future
- [x] Configurable Object Detections
- [ ] Configuration Generator
- [ ] Docker image for server
- [ ] Face blurring

## Contribution
Contributions are greatly welcome. Just make a pull request for any issue that you may want to resolve.
Feel free to add an issue or discussion if you have any questions or comments.

## License
This software is published under the Mozilla Public License 2.0. Please see `LICENSE` for more details.
